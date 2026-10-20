"""Parser for modkit 18-column bedMethyl and differential methylation (DMR) tables."""

from typing import List, Dict, Any
from .clinical_annotations import CLINICAL_METHYLATION_TARGETS


def parse_bedmethyl_content(bed_text_or_lines, case_id: int) -> List[Dict[str, Any]]:
    """
    Parses a modkit bedMethyl or DMR tabular file and identifies clinical promoter
    hypermethylation, hypomethylation, and Allele-Specific Methylation (ASM).
    """
    if isinstance(bed_text_or_lines, str):
        lines = bed_text_or_lines.splitlines()
    else:
        lines = bed_text_or_lines

    records: List[Dict[str, Any]] = []

    for line in lines:
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="ignore")
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("track"):
            continue

        # modkit 18-column format: tab-separated or space-separated after col 9
        parts = line.split("\t")
        if len(parts) < 10:
            # Try whitespace split
            parts = line.split()
            if len(parts) < 10:
                continue

        chrom = parts[0]
        try:
            start_pos = int(parts[1])
            end_pos = int(parts[2])
        except ValueError:
            continue

        name = parts[3] if len(parts) > 3 else "CpG"
        
        # modkit columns:
        # Col 9 (index 9 or 10): Nvalid_cov
        # Col 10: percent_modified (0.0 - 100.0)
        # Col 11: Nmod
        # Col 12: Ncanonical
        try:
            n_valid_cov = int(parts[9])
            percent_mod = float(parts[10])
            n_mod = int(parts[11]) if len(parts) > 11 else int((percent_mod / 100.0) * n_valid_cov)
            n_canonical = int(parts[12]) if len(parts) > 12 else (n_valid_cov - n_mod)
        except (ValueError, IndexError):
            # Fallback for simplified 4-column or 5-column bedGraph: chrom, start, end, pct
            try:
                percent_mod = float(parts[3]) if len(parts) == 4 else float(parts[4])
                n_valid_cov = 30
                n_mod = int((percent_mod / 100.0) * n_valid_cov)
                n_canonical = n_valid_cov - n_mod
            except (ValueError, IndexError):
                continue

        # Phased Allele-Specific Methylation (ASM) only if explicitly present in extended DMR/ASM columns
        hp1_percent = None
        hp2_percent = None
        is_asm = 0
        if len(parts) >= 20:
            try:
                hp1_percent = float(parts[-2])
                hp2_percent = float(parts[-1])
                if abs(hp1_percent - hp2_percent) >= 40.0:
                    is_asm = 1
            except (ValueError, IndexError):
                pass

        # Check overlap with curated clinical gene promoters
        # Extract candidate gene from name
        cand_gene = name
        for sfx in ["_Promoter", "_PWS_ICR", "_Exon1A_ICR", "_ICR1", "_ICR", "_IG_DMR", "_KvDMR1", "_DMR"]:
            if cand_gene.endswith(sfx):
                cand_gene = cand_gene[:-len(sfx)]
                break
        if "_" in cand_gene and cand_gene not in CLINICAL_METHYLATION_TARGETS:
            cand_gene = cand_gene.split("_")[0]
        
        gene_symbol = cand_gene if cand_gene != "CpG" else ""
        clinical_sig = "Non-promoter CpG"
        region_type = "cpg_island"
        status = "Normal"

        for target_gene, info in CLINICAL_METHYLATION_TARGETS.items():
            same_chrom = (info["chrom"].lower() == chrom.lower())
            matches_coord = (same_chrom and max(start_pos, info["start"]) <= min(end_pos, info["end"]))
            matches_name = (same_chrom and (cand_gene.upper() == target_gene.upper() or target_gene.upper() in cand_gene.upper()))
            if matches_coord or matches_name:
                gene_symbol = target_gene
                region_type = info.get("region_type", "Promoter CpG Island")
                clinical_sig = info.get("significance", "")

                if info.get("is_imprinted"):
                    # Imprinting locus: normal is ~50% with ASM
                    if is_asm and abs((hp1_percent or 0) - (hp2_percent or 0)) >= 40.0:
                        status = "Normal (Biallelic Epigenetic Imprint)"
                    elif percent_mod >= info.get("threshold_hyper", 80.0):
                        status = "Loss of Imprinting (Hypermethylated)"
                    elif percent_mod <= info.get("threshold_hypo", 20.0):
                        status = "Loss of Imprinting (Hypomethylated)"
                    else:
                        status = "Normal (Biallelic Epigenetic Imprint)"
                else:
                    # Promoter locus
                    if percent_mod >= info.get("threshold_hyper", 20.0):
                        status = "Hypermethylated (Gene Silenced)"
                    elif percent_mod <= info.get("threshold_normal", 10.0):
                        status = "Unmethylated (Active Promoter)"
                    else:
                        status = "Intermediate / Normal"
                break

        if not gene_symbol and percent_mod >= 70.0:
            status = "Hypermethylated"
        elif not gene_symbol and percent_mod <= 15.0:
            status = "Hypomethylated"

        records.append({
            "case_id": case_id,
            "chrom": chrom,
            "start": start_pos,
            "end": end_pos,
            "name": name,
            "region_type": region_type,
            "gene_symbol": gene_symbol or "Intergenic",
            "n_valid_cov": n_valid_cov,
            "percent_modified": round(percent_mod, 1),
            "n_mod": n_mod,
            "n_canonical": n_canonical,
            "status": status,
            "hp1_percent": hp1_percent,
            "hp2_percent": hp2_percent,
            "is_asm": is_asm,
            "clinical_significance": clinical_sig,
            "notes": ""
        })

    return records
