"""Automated ACMG/AMP 2015 and AMP/ASCO/CAP Somatic classification engine."""

from typing import Dict, Any, List, Tuple
from .clinical_annotations import ACMG_73_GENES, CANCER_DRIVER_GENES


def classify_variant_acmg(v: Dict[str, Any]) -> Tuple[str, List[str], int]:
    """
    Computes automated ACMG classification using ClinGen SVI specifications
    and Tavtigian Bayesian point mapping.
    
    Returns:
        (acmg_class, criteria_list, point_score)
    """
    criteria: List[str] = []
    points: int = 0

    gnomad_af = float(v.get("gnomad_af") or 0.0)
    consequence = (v.get("consequence") or "").lower()
    cadd = float(v.get("cadd_phred") or 0.0)
    revel = float(v.get("revel") or 0.0)
    spliceai = float(v.get("spliceai_ds_max") or 0.0)
    clinvar_sig = (v.get("clinvar_sig") or "").lower()
    gene = (v.get("gene_symbol") or "").upper()

    # 1. Stand-alone Benign BA1: gnomAD Allele frequency > 5%
    if gnomad_af >= 0.05:
        criteria.append("BA1")
        return "Benign", criteria, -99

    # 2. Strong Benign BS1 / BS2: AF > 1% in dominant or population common
    elif gnomad_af >= 0.01:
        criteria.append("BS1")
        points -= 4

    # 3. Pathogenic PVS1: Null variant (nonsense, frameshift, canonical splice donor/acceptor)
    is_null = any(term in consequence for term in [
        "stop_gained", "frameshift", "splice_donor", "splice_acceptor", "start_lost"
    ])
    if is_null and gene:
        criteria.append("PVS1")
        points += 8

    # 4. ClinVar Concordance (PP5 / BP6 calibrated)
    if "pathogenic" in clinvar_sig and "conflict" not in clinvar_sig:
        criteria.append("PP5")
        points += 2
    elif "benign" in clinvar_sig and "conflict" not in clinvar_sig:
        criteria.append("BP6")
        points -= 2

    # 5. In-silico Predictors (PP3 / BP4 via REVEL and SpliceAI)
    # Pejaver et al. 2022 / Walker et al. 2023 calibration
    if revel >= 0.75 or spliceai >= 0.50 or cadd >= 28.0:
        criteria.append("PP3")
        points += 1
    elif (revel > 0 and revel <= 0.25) and (spliceai < 0.10) and (cadd > 0 and cadd <= 15.0):
        criteria.append("BP4")
        points -= 1

    # 6. PM2 (ClinGen SVI 2020 downgraded to Supporting): Absent or extremely rare (AF < 0.0001)
    if gnomad_af < 0.0001 and (v.get("depth", 0) >= 15):
        criteria.append("PM2_Supp")
        points += 1

    # 7. PM1 / Cancer Hotspot domain
    if gene in CANCER_DRIVER_GENES:
        criteria.append("PM1")
        points += 2

    # Map Bayesian score to 5-tier classification
    if points >= 10:
        acmg_class = "Pathogenic"
    elif points >= 6:
        acmg_class = "Likely Pathogenic"
    elif points <= -7:
        acmg_class = "Benign"
    elif points <= -1:
        acmg_class = "Likely Benign"
    else:
        acmg_class = "VUS"

    return acmg_class, criteria, points


def classify_somatic_tier(v: Dict[str, Any]) -> Tuple[str, bool]:
    """
    Classifies somatic variant according to AMP/ASCO/CAP 2017 guidelines:
      - Tier I: Strong Clinical Significance (Biomarker for approved therapy)
      - Tier II: Potential Clinical Significance (Investigational / Trials)
      - Tier III: VUS
      - Tier IV: Benign / Likely Benign
    
    Returns:
        (tier, is_actionable)
    """
    gene = (v.get("gene_symbol") or "").upper()
    clinvar_sig = (v.get("clinvar_sig") or "").lower()
    consequence = (v.get("consequence") or "").lower()
    gnomad_af = float(v.get("gnomad_af") or 0.0)

    # Germline common SNPs are Tier IV
    if gnomad_af >= 0.01:
        return "Tier IV (Benign / Non-actionable)", False

    driver_info = CANCER_DRIVER_GENES.get(gene)
    if driver_info:
        if "pathogenic" in clinvar_sig or any(c in consequence for c in ["stop_gained", "frameshift", "missense"]):
            if driver_info.get("actionable"):
                return "Tier I (Strong Clinical Significance - Actionable)", True
            else:
                return "Tier II (Potential Clinical Significance)", True

    if "pathogenic" in clinvar_sig:
        return "Tier II (Potential Clinical Significance)", True

    return "Tier III (Unknown Clinical Significance - VUS)", False
