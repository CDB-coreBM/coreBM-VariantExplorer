"""Structural variant (SV >= 50bp) parser for Sniffles2, cuteSV, and Severus ONT VCFs."""

import re
from typing import List, Dict, Any
from .clinical_annotations import CANCER_DRIVER_GENES, ACMG_73_GENES


def parse_vcf_sv_content(vcf_text_or_lines, case_id: int) -> List[Dict[str, Any]]:
    """
    Parses a Sniffles2 or cuteSV VCF and returns structured SV records with
    breakpoint coordinates, size classifications, and clinical gene impacts.
    """
    if isinstance(vcf_text_or_lines, str):
        lines = vcf_text_or_lines.splitlines()
    else:
        lines = vcf_text_or_lines

    sv_records: List[Dict[str, Any]] = []

    for line in lines:
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="ignore")
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split("\t")
        if len(parts) < 8:
            continue

        chrom = parts[0]
        start_pos = int(parts[1])
        ref = parts[3]
        alt = parts[4]
        qual = float(parts[5]) if parts[5] != "." else 0.0
        filt = parts[6]
        info_str = parts[7]

        # Parse INFO fields
        info: Dict[str, str] = {}
        for item in info_str.split(";"):
            if "=" in item:
                k, v = item.split("=", 1)
                info[k] = v
            else:
                info[item] = "true"

        # Determine SV Type
        sv_type = info.get("SVTYPE", "")
        if not sv_type:
            if "<DEL>" in alt or (len(ref) > len(alt) and len(ref) >= 50):
                sv_type = "DEL"
            elif "<INS>" in alt or (len(alt) > len(ref) and len(alt) >= 50):
                sv_type = "INS"
            elif "<DUP>" in alt:
                sv_type = "DUP"
            elif "<INV>" in alt:
                sv_type = "INV"
            elif "[" in alt or "]" in alt:
                sv_type = "BND"
            else:
                sv_type = "COMPLEX"

        # SV Length and End Position
        sv_len = 0
        if "SVLEN" in info:
            try: sv_len = abs(int(info["SVLEN"].split(",")[0]))
            except ValueError: pass
        elif sv_type in ("DEL", "INS") and len(ref) != len(alt):
            sv_len = abs(len(alt) - len(ref))

        end_pos = start_pos + sv_len if sv_len > 0 else start_pos
        if "END" in info:
            try: end_pos = int(info["END"])
            except ValueError: pass

        # Parse FORMAT & sample columns
        format_keys = parts[8].split(":") if len(parts) > 8 else []
        sample_vals = parts[9].split(":") if len(parts) > 9 else []
        fmt: Dict[str, str] = dict(zip(format_keys, sample_vals))

        gt = fmt.get("GT", "0/1")
        support = int(info.get("SUPPORT", info.get("RE", fmt.get("DV", 0))))
        total_depth = int(fmt.get("DP", info.get("DP", support * 2 if support else 30)))
        vaf = float(fmt.get("AF", round(support / total_depth, 3) if total_depth > 0 else 0.5))

        # Check tandem repeat status (Sniffles TR / STR annotation)
        is_tr = 1 if ("TR" in info or "STR" in info or "TANDEM" in info) else 0
        tr_bed = info.get("TR", "")

        # Translocation / BND partners
        chr2 = chrom
        pos2 = end_pos
        if sv_type == "BND":
            bnd_match = re.search(r'[\[\]]([^:]+):(\d+)[\[\]]', alt)
            if bnd_match:
                chr2 = bnd_match.group(1)
                pos2 = int(bnd_match.group(2))

        # Genes affected
        genes_affected = info.get("GENES", info.get("ANN", ""))
        gene_list = [g.strip() for g in genes_affected.split(",") if g.strip()]

        # Determine ACMG SV class
        acmg_sv_class = "VUS"
        clinical_impact = "Intronic / Intergenic SV"

        # Check overlap with key cancer or ACMG genes
        matched_genes = [g for g in gene_list if g in CANCER_DRIVER_GENES or g in ACMG_73_GENES]
        if matched_genes:
            if sv_type in ("DEL", "DUP") and sv_len >= 1000:
                acmg_sv_class = "Pathogenic"
                clinical_impact = f"High-impact {sv_type} disrupting canonical reading frame of {', '.join(matched_genes)}"
            elif sv_type == "BND":
                acmg_sv_class = "Likely Pathogenic"
                clinical_impact = f"Chromosomal translocation junction affecting {', '.join(matched_genes)}"
            else:
                acmg_sv_class = "VUS"
                clinical_impact = f"{sv_type} within vicinity of {', '.join(matched_genes)}"
        elif sv_type == "DEL" and sv_len >= 100000:
            acmg_sv_class = "Likely Pathogenic"
            clinical_impact = f"Large contiguous deletion ({sv_len // 1000} kb)"

        sv_records.append({
            "case_id": case_id,
            "chrom": chrom,
            "start": start_pos,
            "end": end_pos,
            "sv_type": sv_type,
            "sv_len": sv_len,
            "qual": qual,
            "filter": filt,
            "genotype": gt,
            "support_reads": support,
            "total_depth": total_depth,
            "vaf": vaf,
            "tandem_repeat": is_tr,
            "tr_bed_hit": tr_bed,
            "chr2": chr2,
            "pos2": pos2,
            "strands": info.get("STRANDS", "+-"),
            "genes_affected": ",".join(gene_list) if gene_list else info.get("GENE", "Intergenic"),
            "exon_overlap": info.get("EXON", ""),
            "cytoband": info.get("CYTOBAND", ""),
            "acmg_sv_class": acmg_sv_class,
            "clinical_impact": clinical_impact,
            "review_status": "Unreviewed",
            "notes": ""
        })

    return sv_records
