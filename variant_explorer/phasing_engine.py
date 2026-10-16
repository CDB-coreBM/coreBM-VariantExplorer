"""
Physical Long-Read Haplotype Phasing & Compound Heterozygosity Engine.
Evaluates:
1. Physical linkage of variants on continuous long reads (HP:i:1 vs HP:i:2).
2. Compound Heterozygosity (cis vs trans):
   - In-Cis (same haplotype) -> Non-diagnostic (carrier of complex allele).
   - In-Trans (opposite haplotypes) -> Confirmed biallelic disruption / diagnostic.
3. Phase block metrics (Block length, N50, phase set ID PS).
"""

from typing import Dict, Any, List, Optional, Tuple


class PhasingEngine:
    """
    Evaluates physical long-read phasing and compound heterozygosity
    for clinical interpretation.
    """

    REVERTED_RECESSIVE_GENES = {
        "CFTR", "DPYD", "SMN1", "GBA", "ATM", "MUTYH", "NPHS1", "NPHS2",
        "PAH", "HEXA", "HBB", "MEFV", "GJB2", "PEX1", "ATP7B", "ABCA4"
    }

    @classmethod
    def evaluate_compound_heterozygosity(cls, variants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Groups variants by gene and analyzes haplotype phasing to distinguish
        in-cis (carrier) from in-trans (affected compound heterozygote).
        """
        gene_groups: Dict[str, List[Dict[str, Any]]] = {}
        for v in variants:
            gene = (v.get("gene_symbol") or "").upper()
            if gene:
                gene_groups.setdefault(gene, []).append(v)

        results = []
        for gene, var_list in gene_groups.items():
            if len(var_list) < 2:
                continue

            # Check if there are at least two qualifying variants (Pathogenic, LP, or VUS)
            qualifying = [
                v for v in var_list
                if (v.get("acmg_class") or v.get("clinical_significance", "")).lower() not in ["benign", "likely benign"]
            ]

            if len(qualifying) >= 2:
                for i in range(len(qualifying)):
                    for j in range(i + 1, len(qualifying)):
                        v1 = qualifying[i]
                        v2 = qualifying[j]

                        # Check phase information
                        ps1 = v1.get("phase_set") or v1.get("ps")
                        ps2 = v2.get("phase_set") or v2.get("ps")
                        gt1 = v1.get("genotype") or ""
                        gt2 = v2.get("genotype") or ""

                        # Determine haplotype
                        hp1 = None
                        if "|" in gt1:
                            parts = gt1.split("|")
                            if parts[0] == "1": hp1 = 1
                            elif parts[1] == "1": hp1 = 2

                        hp2 = None
                        if "|" in gt2:
                            parts = gt2.split("|")
                            if parts[0] == "1": hp2 = 1
                            elif parts[1] == "1": hp2 = 2

                        # If explicitly annotated with haplotype
                        if v1.get("haplotype"): hp1 = v1.get("haplotype")
                        if v2.get("haplotype"): hp2 = v2.get("haplotype")

                        is_phased = (ps1 is not None and ps2 is not None and ps1 == ps2) or (hp1 is not None and hp2 is not None)

                        if is_phased and hp1 and hp2:
                            if hp1 != hp2:
                                config = "In-Trans (Opposite Haplotypes)"
                                clinical_impact = "CONFIRMED COMPOUND HETEROZYGOTE (Biallelic disruption - Diagnostic)"
                                status = "Pathogenic Biallelic Pair"
                            else:
                                config = "In-Cis (Same Haplotype)"
                                clinical_impact = "Monoallelic Cis-Complex Allele (Patient is an asymptomatic carrier)"
                                status = "Carrier / Non-Diagnostic"
                        else:
                            config = "Unphased (Phase set boundary break or unlinked reads)"
                            clinical_impact = "Potential compound heterozygosity requires parental trio testing to resolve phase"
                            status = "Unresolved Phase"

                        results.append({
                            "gene_symbol": gene,
                            "variant_1": f"{v1.get('hgvs_c', '')} ({v1.get('hgvs_p', '')})",
                            "variant_2": f"{v2.get('hgvs_c', '')} ({v2.get('hgvs_p', '')})",
                            "phase_configuration": config,
                            "clinical_interpretation": clinical_impact,
                            "diagnostic_status": status,
                            "phase_set": ps1 if ps1 == ps2 else "Split Blocks",
                            "v1_id": v1.get("id"),
                            "v2_id": v2.get("id")
                        })

        return results

    @staticmethod
    def calculate_phase_block_n50(block_lengths: List[int], total_genome_length: int = 3100000000) -> int:
        """
        Calculates phase block N50 length from a list of phased span lengths.
        """
        if not block_lengths:
            return 0
        sorted_lengths = sorted(block_lengths, reverse=True)
        half_sum = sum(sorted_lengths) / 2.0
        running_sum = 0
        for l in sorted_lengths:
            running_sum += l
            if running_sum >= half_sum:
                return l
        return sorted_lengths[0]
