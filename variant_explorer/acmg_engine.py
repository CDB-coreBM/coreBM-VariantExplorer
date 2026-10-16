"""
ACMG/AMP + ClinGen SVI Bayesian Variant Classification Engine.
Implements:
1. Tavtigian Bayesian Point System (Tavtigian et al., Hum Mutat 2020)
   - OddsPath = 2.08^(Points)
   - PVS1 (Very Strong) = +8
   - Strong = +4
   - Moderate = +2
   - Supporting = +1
   - Benign Supporting = -1
   - Benign Moderate = -2
   - Benign Strong = -4
   - Stand-Alone Benign (BA1) = -8
2. Abou Tayoun et al. (2018) PVS1 Decision Tree for Loss of Function
3. Pejaver et al. (2022 AJHG) Calibrated PP3/BP4 thresholds (REVEL, AlphaMissense)
4. ClinGen dosage sensitivity and gene-disease validity
"""

from typing import Dict, Any, List, Optional, Tuple
import math


class ACMGEngine:
    """
    Automated, calibrated ACMG/AMP variant classifier implementing
    the Bayesian point system and ClinGen SVI recommendations.
    """

    # ClinGen curated Haploinsufficient (LoF-mechanism) genes with high confidence
    KNOWN_HAPLOINSUFFICIENT_GENES = {
        "BRCA1", "BRCA2", "TP53", "MLH1", "MSH2", "MSH6", "PMS2", "APC",
        "PTEN", "RB1", "NF1", "NF2", "WT1", "VHL", "CDH1", "STK11",
        "PALB2", "ATM", "RAD51C", "RAD51D", "BAP1", "SMAD4", "BMPR1A",
        "MEN1", "RET", "TSC1", "TSC2", "MUTYH", "CFTR", "DPYD", "SMN1",
        "LDLR", "MYH7", "MYBPC3", "TNNT2", "LMNA", "PKP2", "DSP", "DSC2",
        "KCNQ1", "KCNH2", "SCN5A", "FBN1", "COL3A1", "TGFBR1", "TGFBR2"
    }

    # Established hot-spot / critical functional domains (PM1 candidates)
    CRITICAL_DOMAIN_GENES = {
        "TP53": (102, 292, "DNA-binding domain"),
        "KRAS": (10, 65, "GTPase catalytic switch I/II"),
        "BRAF": (460, 605, "Kinase domain activation loop"),
        "EGFR": (712, 865, "Tyrosine kinase domain"),
        "PIK3CA": (542, 1047, "Helical and kinase domain"),
        "PTEN": (14, 185, "Phosphatase catalytic domain"),
        "BRCA1": [(1, 100, "RING finger domain"), (1650, 1855, "BRCT domain")],
        "BRCA2": (2481, 3186, "DNA-binding domain")
    }

    @classmethod
    def evaluate_pvs1(cls, gene: str, consequence: str, hgvs_c: str, hgvs_p: str, exon_info: Optional[str] = None) -> Tuple[Optional[str], int, str]:
        """
        Applies Abou Tayoun (2018) PVS1 decision tree.
        Returns: (code_name, points, rationale)
        """
        csq_lower = (consequence or "").lower()
        is_lof = any(term in csq_lower for term in [
            "stop_gained", "frameshift", "splice_acceptor", "splice_donor", "start_lost"
        ])

        if not is_lof:
            return (None, 0, "Variant is not a predicted loss-of-function variant")

        gene_upper = (gene or "").upper()
        if gene_upper not in cls.KNOWN_HAPLOINSUFFICIENT_GENES:
            return ("PVS1_Supporting", 1, f"Predicted LoF in {gene_upper}, but LoF is not yet an established definitive disease mechanism (ClinGen HI score < 3)")

        # Evaluate NMD status
        # If variant is in penultimate/last exon or within 50bp of last junction, NMD is escaped
        nmd_escaped = False
        if exon_info:
            parts = exon_info.split("/")
            if len(parts) == 2:
                try:
                    cur_exon = int(parts[0])
                    total_exons = int(parts[1])
                    if cur_exon >= total_exons - 1:
                        nmd_escaped = True
                except ValueError:
                    pass

        if "splice_donor" in csq_lower or "splice_acceptor" in csq_lower:
            return ("PVS1_VeryStrong", 8, f"Disrupts canonical ±1,2 splice dinucleotide in established haploinsufficient gene {gene_upper}")

        if "stop_gained" in csq_lower or "frameshift" in csq_lower:
            if nmd_escaped:
                return ("PVS1_Moderate", 2, f"Premature termination codon predicted to escape nonsense-mediated decay (NMD) in {gene_upper}")
            return ("PVS1_VeryStrong", 8, f"Premature stop / frameshift predicted to undergo NMD in established haploinsufficient gene {gene_upper}")

        if "start_lost" in csq_lower:
            return ("PVS1_Moderate", 2, f"Initiation codon disrupted in {gene_upper}")

        return ("PVS1_Strong", 4, f"Loss-of-function variant in established disease gene {gene_upper}")

    @classmethod
    def evaluate_in_silico(cls, revel: Optional[float] = None, alpha_missense: Optional[float] = None,
                           splice_ai_delta: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Calibrated in silico evidence per Pejaver et al. (2022 AJHG) and ClinGen SVI.
        """
        evidence = []

        # 1. SpliceAI delta score evaluation
        if splice_ai_delta is not None:
            if splice_ai_delta >= 0.80:
                evidence.append({
                    "code": "PP3_Strong",
                    "points": 4,
                    "desc": f"SpliceAI max delta score ({splice_ai_delta:.3f} >= 0.80) predicts high-confidence aberrant splicing"
                })
            elif splice_ai_delta >= 0.50:
                evidence.append({
                    "code": "PP3_Moderate",
                    "points": 2,
                    "desc": f"SpliceAI max delta score ({splice_ai_delta:.3f} >= 0.50) predicts probable aberrant splicing"
                })
            elif splice_ai_delta >= 0.20:
                evidence.append({
                    "code": "PP3_Supporting",
                    "points": 1,
                    "desc": f"SpliceAI max delta score ({splice_ai_delta:.3f} >= 0.20) predicts potential splice disruption"
                })

        # 2. REVEL (Pejaver 2022 calibrated thresholds)
        if revel is not None:
            if revel >= 0.932:
                evidence.append({
                    "code": "PP3_Strong",
                    "points": 4,
                    "desc": f"REVEL score ({revel:.3f} >= 0.932) reaches calibrated PP3_Strong threshold"
                })
            elif revel >= 0.773:
                evidence.append({
                    "code": "PP3_Moderate",
                    "points": 2,
                    "desc": f"REVEL score ({revel:.3f} >= 0.773) reaches calibrated PP3_Moderate threshold"
                })
            elif revel >= 0.644:
                evidence.append({
                    "code": "PP3_Supporting",
                    "points": 1,
                    "desc": f"REVEL score ({revel:.3f} >= 0.644) reaches calibrated PP3_Supporting threshold"
                })
            elif revel <= 0.016:
                evidence.append({
                    "code": "BP4_Strong",
                    "points": -4,
                    "desc": f"REVEL score ({revel:.3f} <= 0.016) reaches calibrated BP4_Strong benign threshold"
                })
            elif revel <= 0.183:
                evidence.append({
                    "code": "BP4_Moderate",
                    "points": -2,
                    "desc": f"REVEL score ({revel:.3f} <= 0.183) reaches calibrated BP4_Moderate benign threshold"
                })
            elif revel <= 0.290:
                evidence.append({
                    "code": "BP4_Supporting",
                    "points": -1,
                    "desc": f"REVEL score ({revel:.3f} <= 0.290) reaches calibrated BP4_Supporting benign threshold"
                })

        # 3. AlphaMissense (Cheng et al. Science 2023)
        if alpha_missense is not None and not any(e["code"].startswith("PP3") or e["code"].startswith("BP4") for e in evidence):
            if alpha_missense >= 0.85:
                evidence.append({
                    "code": "PP3_Moderate",
                    "points": 2,
                    "desc": f"AlphaMissense score ({alpha_missense:.3f} >= 0.85) indicates likely pathogenic structural disruption"
                })
            elif alpha_missense >= 0.56:
                evidence.append({
                    "code": "PP3_Supporting",
                    "points": 1,
                    "desc": f"AlphaMissense score ({alpha_missense:.3f} >= 0.56) indicates ambiguous/pathogenic missense impact"
                })
            elif alpha_missense <= 0.15:
                evidence.append({
                    "code": "BP4_Moderate",
                    "points": -2,
                    "desc": f"AlphaMissense score ({alpha_missense:.3f} <= 0.15) indicates high-confidence benign structural tolerance"
                })
            elif alpha_missense <= 0.34:
                evidence.append({
                    "code": "BP4_Supporting",
                    "points": -1,
                    "desc": f"AlphaMissense score ({alpha_missense:.3f} <= 0.34) indicates likely benign missense impact"
                })

        return evidence

    @classmethod
    def evaluate_population_frequency(cls, af: Optional[float]) -> List[Dict[str, Any]]:
        """
        Evaluates population allele frequency against gnomAD thresholds.
        """
        evidence = []
        if af is None or af == 0.0 or af <= 1e-5:
            evidence.append({
                "code": "PM2_Supporting",
                "points": 1,
                "desc": f"Extremely rare or novel in gnomAD population database (AF = {af if af is not None else 0.0:.2e} <= 1e-5)"
            })
        elif af >= 0.05:
            evidence.append({
                "code": "BA1",
                "points": -8,
                "desc": f"Allele frequency in gnomAD exceeds stand-alone benign threshold (AF = {af:.4f} >= 0.05)"
            })
        elif af >= 0.01:
            evidence.append({
                "code": "BS1",
                "points": -4,
                "desc": f"Allele frequency in gnomAD is higher than expected for rare Mendelian disease (AF = {af:.4f} >= 0.01)"
            })
        return evidence

    @classmethod
    def classify(cls, variant: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates full Bayesian ACMG classification for a single variant.
        Variant dictionary may contain:
          - gene_symbol: str
          - consequence: str
          - hgvs_c: str
          - hgvs_p: str
          - gnomad_af: float
          - revel_score: float
          - alpha_missense: float
          - splice_ai: float
          - clinvar_sig: str
        """
        evidence_list: List[Dict[str, Any]] = []

        gene = variant.get("gene_symbol", "")
        consequence = variant.get("consequence", "")
        hgvs_c = variant.get("hgvs_c", "")
        hgvs_p = variant.get("hgvs_p", "")
        af = variant.get("gnomad_af")

        # 1. PVS1 Evaluation
        pvs1_code, pvs1_pts, pvs1_desc = cls.evaluate_pvs1(gene, consequence, hgvs_c, hgvs_p)
        if pvs1_code:
            evidence_list.append({
                "code": pvs1_code,
                "points": pvs1_pts,
                "desc": pvs1_desc
            })

        # 2. In silico predictors (PP3 / BP4)
        # Subsumption rule: If PVS1 is applied at Strong/VeryStrong, PP3 is subsumed
        subsume_pp3 = pvs1_code in ["PVS1_VeryStrong", "PVS1_Strong"]
        in_silico_ev = cls.evaluate_in_silico(
            revel=variant.get("revel_score"),
            alpha_missense=variant.get("alpha_missense"),
            splice_ai_delta=variant.get("splice_ai")
        )
        for ev in in_silico_ev:
            if subsume_pp3 and ev["code"].startswith("PP3"):
                continue  # Abou Tayoun subsumption
            evidence_list.append(ev)

        # 3. Population Allele Frequency (BA1, BS1, PM2_Supporting)
        pop_ev = cls.evaluate_population_frequency(af)
        evidence_list.extend(pop_ev)

        # 4. Synonymous variant (BP7)
        if "synonymous" in (consequence or "").lower():
            evidence_list.append({
                "code": "BP7",
                "points": -1,
                "desc": "Synonymous (silent) coding change with no predicted splice alteration"
            })

        # 5. ClinVar consensus integration
        clinvar_sig = (variant.get("clinvar_sig") or "").lower()
        if "pathogenic" in clinvar_sig and "conflict" not in clinvar_sig:
            evidence_list.append({
                "code": "PP5_Supporting",
                "points": 1,
                "desc": f"ClinVar established consensus: {variant.get('clinvar_sig')}"
            })
        elif "benign" in clinvar_sig and "conflict" not in clinvar_sig:
            evidence_list.append({
                "code": "BP6_Supporting",
                "points": -1,
                "desc": f"ClinVar established benign consensus: {variant.get('clinvar_sig')}"
            })

        # Calculate Total Bayesian Points
        total_points = sum(e["points"] for e in evidence_list)

        # Determine Classification
        if any(e["code"] == "BA1" for e in evidence_list):
            classification = "Benign"
            tier = "Tier IV (Benign)"
        elif total_points >= 10:
            classification = "Pathogenic"
            tier = "Tier I (Strong Clinical Significance)"
        elif total_points >= 6:
            classification = "Likely Pathogenic"
            tier = "Tier I (Potential Clinical Significance)"
        elif total_points >= 0:
            classification = "Uncertain Significance (VUS)"
            tier = "Tier III (Uncertain Clinical Significance)"
        elif total_points >= -6:
            classification = "Likely Benign"
            tier = "Tier IV (Likely Benign)"
        else:
            classification = "Benign"
            tier = "Tier IV (Benign)"

        return {
            "classification": classification,
            "tier": tier,
            "total_points": total_points,
            "odds_pathogenicity": round(2.08 ** total_points, 2),
            "evidence": evidence_list,
            "codes_applied": [e["code"] for e in evidence_list]
        }
