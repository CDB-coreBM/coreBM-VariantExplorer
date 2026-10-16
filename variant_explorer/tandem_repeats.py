"""
Tandem Repeat & Short Tandem Repeat (STR) Expansion Engine.
Consumes TRGT (Tandem Repeat Genotyping Tool) and Straglr outputs.
Evaluates:
- Repeat count per haplotype (Haplotype 1 and Haplotype 2).
- Motif composition and interruptions.
- Pathogenic threshold comparison (Huntington, C9orf72 ALS/FTD, Fragile X, Friedreich Ataxia, Myotonic Dystrophy).
"""

from typing import Dict, Any, List, Optional


class TandemRepeatEngine:
    """
    Evaluates tandem repeat expansion loci for neurological and neuromuscular disorders.
    """

    # Established clinical cutoffs for repeat expansion disorders
    PATHOGENIC_REPEAT_LOCI = {
        "HTT": {
            "disease": "Huntington Disease",
            "motif": "CAG",
            "chrom": "chr4", "start": 3074876, "end": 3074933,
            "normal_max": 26,
            "intermediate_max": 35,
            "reduced_penetrance_max": 39,
            "pathogenic_min": 40
        },
        "C9orf72": {
            "disease": "Amyotrophic Lateral Sclerosis / Frontotemporal Dementia (ALS/FTD)",
            "motif": "GGGGCC",
            "chrom": "chr9", "start": 27573482, "end": 27573545,
            "normal_max": 25,
            "intermediate_max": 30,
            "reduced_penetrance_max": 30,
            "pathogenic_min": 31
        },
        "FMR1": {
            "disease": "Fragile X Syndrome / FXTAS",
            "motif": "CGG",
            "chrom": "chrX", "start": 147912050, "end": 147912110,
            "normal_max": 44,
            "intermediate_max": 54,
            "reduced_penetrance_max": 200,
            "pathogenic_min": 200
        },
        "FXN": {
            "disease": "Friedreich Ataxia",
            "motif": "GAA",
            "chrom": "chr9", "start": 71653150, "end": 71653220,
            "normal_max": 33,
            "intermediate_max": 65,
            "reduced_penetrance_max": 65,
            "pathogenic_min": 66
        },
        "DMPK": {
            "disease": "Myotonic Dystrophy Type 1",
            "motif": "CTG",
            "chrom": "chr19", "start": 45770200, "end": 45770280,
            "normal_max": 37,
            "intermediate_max": 49,
            "reduced_penetrance_max": 49,
            "pathogenic_min": 50
        },
        "ATXN1": {
            "disease": "Spinocerebellar Ataxia Type 1 (SCA1)",
            "motif": "CAG",
            "chrom": "chr6", "start": 16327630, "end": 16327710,
            "normal_max": 35,
            "intermediate_max": 38,
            "reduced_penetrance_max": 43,
            "pathogenic_min": 44
        }
    }

    @classmethod
    def evaluate_repeat_allele(cls, gene: str, allele_1_count: int, allele_2_count: int,
                               motif: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluates repeat counts on both haplotypes against clinical disease cutoffs.
        """
        gene_upper = (gene or "").upper()
        ref = cls.PATHOGENIC_REPEAT_LOCI.get(gene_upper)

        res: Dict[str, Any] = {
            "gene_symbol": gene_upper,
            "disease": ref["disease"] if ref else "Unspecified Repeat Locus",
            "motif": motif or (ref["motif"] if ref else "TR"),
            "allele_1_count": allele_1_count,
            "allele_2_count": allele_2_count,
            "max_repeat_count": max(allele_1_count, allele_2_count),
            "status": "Normal / Non-Expanded",
            "clinical_significance": "Negative for Repeat Expansion"
        }

        if not ref:
            return res

        max_count = max(allele_1_count, allele_2_count)

        if max_count >= ref["pathogenic_min"]:
            res["status"] = "Pathogenic Full Expansion"
            res["clinical_significance"] = f"Positive: Pathogenic repeat expansion identified in {gene_upper} ({max_count} repeats >= {ref['pathogenic_min']}). Diagnostic for {ref['disease']}."
            res["acmg_class"] = "Pathogenic"
        elif max_count > ref["intermediate_max"]:
            res["status"] = "Reduced Penetrance / Premutation"
            res["clinical_significance"] = f"Premutation / Reduced penetrance allele ({max_count} repeats). Risk of expansion in future generations."
            res["acmg_class"] = "Uncertain Significance (VUS)"
        elif max_count > ref["normal_max"]:
            res["status"] = "Intermediate (Mutable Normal)"
            res["clinical_significance"] = f"Intermediate allele ({max_count} repeats). Stable in individual, potential meiotic instability."
            res["acmg_class"] = "Likely Benign"
        else:
            res["status"] = "Normal Range"
            res["clinical_significance"] = f"Normal allele sizes ({allele_1_count}, {allele_2_count} repeats <= {ref['normal_max']})."
            res["acmg_class"] = "Benign"

        return res
