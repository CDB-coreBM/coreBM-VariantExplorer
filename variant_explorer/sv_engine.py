"""
High-Performance Structural Variant (SV) & Complex Rearrangement Engine.
Consumes Sniffles2, Severus, and cuteSV VCFs.
Features:
1. Breakend (BND) graph reconstruction and reciprocal translocation pairing.
2. Single-molecule long-read support metrics (RNAMES, STRANDS, CIPOS, VAF).
3. Gene overlap and oncogenic fusion consequence prediction.
4. ClinGen dosage sensitivity scoring for CNVs (losses and gains).
"""

import os
import re
from typing import Dict, Any, List, Optional, Tuple


class SVEngine:
    """
    Parses and interprets long-read structural variants including
    complex rearrangements and gene fusions.
    """

    # Known recurrent oncogenic fusion pairs
    RECURRENT_FUSIONS = {
        ("BCR", "ABL1"): "t(9;22)(q34.1;q11.2) Philadelphia Chromosome - CML / B-ALL targetable by TKIs (Imatinib, Dasatinib)",
        ("ABL1", "BCR"): "t(9;22)(q34.1;q11.2) Philadelphia Chromosome Reciprocal translocation derivative",
        ("PML", "RARA"): "t(15;17)(q24.1;q21.2) Acute Promyelocytic Leukemia (APL) - responsive to ATRA + Arsenic Trioxide",
        ("TMPRSS2", "ERG"): "del(21)(q22.2q22.3) Prostate adenocarcinoma recurrent androgen-driven fusion",
        ("EML4", "ALK"): "inv(2)(p21p23) Non-small cell lung cancer (NSCLC) - sensitive to ALK inhibitors (Alectinib, Crizotinib)",
        ("KIF5B", "RET"): "inv(10)(p11.2q11.2) NSCLC - responsive to Selpercatinib",
        ("EWSR1", "FLI1"): "t(11;22)(q24;q12) Ewing Sarcoma diagnostic rearrangement",
        ("SS18", "SSX1"): "t(X;18)(p11.2;q11.2) Synovial sarcoma diagnostic fusion",
        ("IGH", "BCL2"): "t(14;18)(q32;q21) Follicular lymphoma hallmark rearrangement",
        ("IGH", "MYC"): "t(8;14)(q24;q32) Burkitt lymphoma hallmark rearrangement"
    }

    # Dosage sensitive cancer and developmental genes
    CLINGEN_DOSAGE_GENES = {
        "TP53": {"HI": 3, "TS": 1, "disease": "Li-Fraumeni syndrome / broad tumor predisposition"},
        "BRCA1": {"HI": 3, "TS": 1, "disease": "Hereditary Breast and Ovarian Cancer"},
        "BRCA2": {"HI": 3, "TS": 1, "disease": "Hereditary Breast and Ovarian Cancer"},
        "PTEN": {"HI": 3, "TS": 1, "disease": "Cowden syndrome / Hamartoma tumor syndrome"},
        "RB1": {"HI": 3, "TS": 1, "disease": "Retinoblastoma"},
        "NF1": {"HI": 3, "TS": 1, "disease": "Neurofibromatosis type 1"},
        "SMN1": {"HI": 3, "TS": 1, "disease": "Spinal Muscular Atrophy"},
        "CYP2D6": {"HI": 0, "TS": 0, "disease": "Pharmacogenomic metabolism alteration"},
        "EGFR": {"HI": 1, "TS": 3, "disease": "Oncogenic focal amplification / tyrosine kinase activation"},
        "ERBB2": {"HI": 1, "TS": 3, "disease": "HER2 amplification in breast/gastric carcinomas"},
        "MYC": {"HI": 1, "TS": 3, "disease": "Oncogenic focal amplification / Burkitt rearrangement"}
    }

    @staticmethod
    def parse_bnd_alt(alt: str) -> Optional[Tuple[str, int, str]]:
        """
        Parses VCF Breakend notation:
        Examples:
          - N[chr22:23290413[ -> target chrom, pos, orientation
          - ]chr22:23290413]N
          - [chr22:23290413[N
          - N]chr22:23290413]
        Returns: (target_chrom, target_pos, orientation)
        """
        match = re.search(r"[\[\]]([^:]+):(\d+)[\[\]]", alt)
        if match:
            target_chrom = match.group(1).replace("chr", "")
            target_pos = int(match.group(2))
            return (target_chrom, target_pos, alt)
        return None

    @classmethod
    def analyze_sv_record(cls, sv: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhances an SV record with clinical interpretations, fusion prediction,
        and ClinGen dosage assessment.
        """
        enhanced = dict(sv)

        sv_type = (enhanced.get("sv_type") or "SV").upper()
        gene = enhanced.get("gene_symbol") or ""
        length = abs(int(enhanced.get("length") or 0))

        # 1. Breakend / Translocation Analysis
        alt = enhanced.get("alt") or ""
        bnd_info = cls.parse_bnd_alt(alt) if sv_type == "BND" else None
        if bnd_info:
            target_chrom, target_pos, _ = bnd_info
            enhanced["mate_chrom"] = target_chrom
            enhanced["mate_pos"] = target_pos

            # Check if this forms a known fusion partner
            partner_gene = enhanced.get("partner_gene") or ""
            fusion_key = (gene, partner_gene)
            if fusion_key in cls.RECURRENT_FUSIONS:
                enhanced["is_known_fusion"] = True
                enhanced["fusion_desc"] = cls.RECURRENT_FUSIONS[fusion_key]
                enhanced["acmg_class"] = "Pathogenic"
                enhanced["clinical_significance"] = "Tier I (Established Oncogenic Driver)"
            else:
                enhanced["is_known_fusion"] = False
                enhanced["fusion_desc"] = f"Translocation between {enhanced.get('chrom')}:{enhanced.get('start')} and chr{target_chrom}:{target_pos}"

        # 2. Dosage Sensitivity Scoring (Deletions & Duplications)
        dosage_info = cls.CLINGEN_DOSAGE_GENES.get(gene.upper())
        if dosage_info:
            if sv_type in ["DEL", "DELETION"] and dosage_info.get("HI") == 3:
                enhanced["acmg_class"] = "Pathogenic"
                enhanced["dosage_impact"] = f"ClinGen High-Confidence Haploinsufficiency (HI=3): {dosage_info['disease']}"
                enhanced["clinical_significance"] = "Tier I (ClinGen Pathogenic CNV Loss)"
            elif sv_type in ["DUP", "DUPLICATION", "AMP"] and dosage_info.get("TS") == 3:
                enhanced["acmg_class"] = "Pathogenic"
                enhanced["dosage_impact"] = f"ClinGen High-Confidence Triplosensitivity (TS=3): {dosage_info['disease']}"
                enhanced["clinical_significance"] = "Tier I (ClinGen Pathogenic CNV Gain)"

        # 3. Size and confidence tiering
        support = enhanced.get("support") or 0
        vaf = enhanced.get("vaf") or 0.0
        if support >= 15 and vaf >= 0.35:
            enhanced["confidence_tier"] = "High Confidence (Clonal Long-Read Call)"
        elif support >= 5:
            enhanced["confidence_tier"] = "Moderate Confidence"
        else:
            enhanced["confidence_tier"] = "Low Support (Candidate Mosaic / Subclonal)"

        return enhanced

    @classmethod
    def group_fusion_candidates(cls, sv_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Groups BNDs and large rearrangements into reciprocal fusion pairs.
        """
        fusions = []
        bnd_records = [sv for sv in sv_list if sv.get("sv_type") == "BND"]

        # Track processed IDs
        paired_ids = set()

        for bnd in bnd_records:
            bnd_id = bnd.get("id")
            if bnd_id in paired_ids:
                continue

            mate_id = bnd.get("mate_id") or ""
            # Search for mate in records
            mate = next((r for r in bnd_records if r.get("id") == mate_id), None)
            if mate:
                paired_ids.add(bnd_id)
                paired_ids.add(mate.get("id"))
                gene1 = bnd.get("gene_symbol") or "Locus_1"
                gene2 = mate.get("gene_symbol") or "Locus_2"
                fusion_pair = f"{gene1}::{gene2}"
                known_desc = cls.RECURRENT_FUSIONS.get((gene1, gene2)) or cls.RECURRENT_FUSIONS.get((gene2, gene1))
                fusions.append({
                    "fusion_name": fusion_pair,
                    "chrom1": bnd.get("chrom"),
                    "pos1": bnd.get("start"),
                    "chrom2": mate.get("chrom"),
                    "pos2": mate.get("start"),
                    "gene1": gene1,
                    "gene2": gene2,
                    "is_known_driver": known_desc is not None,
                    "description": known_desc or f"Reciprocal translocation breakend pair ({fusion_pair})",
                    "support": max(bnd.get("support", 0), mate.get("support", 0)),
                    "bnd1_id": bnd_id,
                    "bnd2_id": mate.get("id")
                })
            else:
                # Unpaired BND or trans-chromosomal junction
                gene1 = bnd.get("gene_symbol") or "Unknown"
                fusions.append({
                    "fusion_name": f"{gene1} Rearrangement",
                    "chrom1": bnd.get("chrom"),
                    "pos1": bnd.get("start"),
                    "chrom2": bnd.get("mate_chrom") or bnd.get("chrom"),
                    "pos2": bnd.get("mate_pos") or bnd.get("end"),
                    "gene1": gene1,
                    "gene2": bnd.get("partner_gene") or "Intergenic",
                    "is_known_driver": bnd.get("is_known_fusion", False),
                    "description": bnd.get("fusion_desc") or "Unpaired translocation breakpoint",
                    "support": bnd.get("support", 0),
                    "bnd1_id": bnd_id,
                    "bnd2_id": None
                })

        return fusions
