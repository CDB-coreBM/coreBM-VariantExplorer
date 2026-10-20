"""VCF parser for ONT small variants (SNVs and Indels) from Clair3 and DeepVariant."""

import gzip
import re
from typing import List, Dict, Any, Optional
from .acmg_classifier import classify_variant_acmg, classify_somatic_tier


def parse_vcf_snv_content(vcf_text_or_lines, case_id: int) -> List[Dict[str, Any]]:
    """
    Parses a Clair3/DeepVariant VCF file content and returns structured variant dictionaries
    annotated with phase sets (PS/HP), consequences, and ACMG classifications.
    """
    if isinstance(vcf_text_or_lines, str):
        lines = vcf_text_or_lines.splitlines()
    else:
        lines = vcf_text_or_lines

    csq_format: List[str] = []
    variants: List[Dict[str, Any]] = []

    for line in lines:
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="ignore")
        line = line.strip()
        if not line:
            continue

        # Header inspection for CSQ (VEP) or ANN (SnpEff)
        if line.startswith("##INFO=<ID=CSQ,"):
            m = re.search(r'Format:\s*([^\">]+)', line)
            if m:
                csq_format = [col.strip() for col in m.group(1).split("|")]
            continue

        if line.startswith("#"):
            continue

        parts = line.split("\t")
        if len(parts) < 8:
            continue

        chrom = parts[0]
        pos = int(parts[1])
        ref = parts[3]
        alt_str = parts[4]
        qual = float(parts[5]) if parts[5] != "." else 0.0
        filt = parts[6]
        info_str = parts[7]

        # Parse INFO fields
        info_dict: Dict[str, str] = {}
        for item in info_str.split(";"):
            if "=" in item:
                k, v = item.split("=", 1)
                info_dict[k] = v
            else:
                info_dict[item] = "true"

        # Parse FORMAT & sample columns
        format_keys = parts[8].split(":") if len(parts) > 8 else []
        sample_vals = parts[9].split(":") if len(parts) > 9 else []
        fmt: Dict[str, str] = dict(zip(format_keys, sample_vals))

        gt = fmt.get("GT", "./.")
        phase_set_raw = fmt.get("PS", None)
        phase_set = None
        if phase_set_raw and phase_set_raw not in (".", ""):
            phase_set = str(phase_set_raw)

        # Physical phasing strictly requires '|' delimiter per VCF 4.3 specification
        if "|" in gt:
            if gt == "1|0":
                haplotype = 1
            elif gt == "0|1":
                haplotype = 2
            elif gt in ("1|1", "1|2", "2|1"):
                haplotype = 3
            else:
                haplotype = None
        else:
            haplotype = None

        # Depth and Allelic Depth
        depth = 0
        if "DP" in fmt and fmt["DP"].isdigit():
            depth = int(fmt["DP"])
        elif "DP" in info_dict and info_dict["DP"].isdigit():
            depth = int(info_dict["DP"])

        alt_depth = 0
        if "AD" in fmt:
            ad_parts = fmt["AD"].split(",")
            if len(ad_parts) > 1 and ad_parts[1].isdigit():
                alt_depth = int(ad_parts[1])
                if depth == 0 and ad_parts[0].isdigit():
                    depth = int(ad_parts[0]) + alt_depth

        vaf = 0.0
        if "AF" in fmt and fmt["AF"] not in (".", ""):
            try:
                vaf = float(fmt["AF"])
            except ValueError:
                vaf = 0.0
        elif depth > 0:
            vaf = round(alt_depth / depth, 3)

        # Handle CSQ VEP annotations
        csq_raw = info_dict.get("CSQ", "")
        gene_symbol = info_dict.get("GENE", "")
        consequence = "missense_variant" if len(ref) == len(alt_str) == 1 else "frameshift_variant"
        hgvs_c = ""
        hgvs_p = ""
        transcript_id = ""
        exon = ""
        gnomad_af = None
        for af_key in ("AF_POPMAX", "gnomAD_AF", "MAX_AF", "gnomad_af", "gnomADg_AF", "gnomADe_AF"):
            val = info_dict.get(af_key, "").strip()
            if val and val != ".":
                try:
                    gnomad_af = float(val)
                    break
                except ValueError:
                    pass

        clinvar_sig = info_dict.get("CLNSIG", "")
        clinvar_id = info_dict.get("CLNACC", "")
        cadd = None
        if "CADD_PHRED" in info_dict and info_dict["CADD_PHRED"] not in (".", ""):
            try: cadd = float(info_dict["CADD_PHRED"])
            except ValueError: pass
        revel = None
        if "REVEL" in info_dict and info_dict["REVEL"] not in (".", ""):
            try: revel = float(info_dict["REVEL"])
            except ValueError: pass
        spliceai = None
        if "SpliceAI_DS_max" in info_dict and info_dict["SpliceAI_DS_max"] not in (".", ""):
            try: spliceai = float(info_dict["SpliceAI_DS_max"])
            except ValueError: pass

        if csq_raw and csq_format:
            first_csq = csq_raw.split(",")[0].split("|")
            csq_map = dict(zip(csq_format, first_csq))
            consequence = csq_map.get("Consequence", consequence)
            gene_symbol = csq_map.get("SYMBOL", gene_symbol)
            transcript_id = csq_map.get("Feature", transcript_id)
            hgvs_c = csq_map.get("HGVSc", hgvs_c)
            hgvs_p = csq_map.get("HGVSp", hgvs_p)
            exon = csq_map.get("EXON", exon)
            
            # Extract population allele frequency across standard VEP fields
            for af_key in ("AF_POPMAX", "gnomAD_AF", "MAX_AF", "gnomad_af", "gnomADg_AF", "gnomADe_AF", "AF"):
                val = csq_map.get(af_key, "").strip()
                if val and val != ".":
                    try:
                        gnomad_af = float(val)
                        break
                    except ValueError:
                        pass
                        
            if csq_map.get("CLIN_SIG"):
                clinvar_sig = csq_map["CLIN_SIG"]
            if csq_map.get("CADD_PHRED") and csq_map["CADD_PHRED"] not in (".", ""):
                try: cadd = float(csq_map["CADD_PHRED"])
                except ValueError: pass
            if csq_map.get("REVEL") and csq_map["REVEL"] not in (".", ""):
                try: revel = float(csq_map["REVEL"])
                except ValueError: pass
            if csq_map.get("SpliceAI_DS_max") and csq_map["SpliceAI_DS_max"] not in (".", ""):
                try: spliceai = float(csq_map["SpliceAI_DS_max"])
                except ValueError: pass

        # Normalize protein change: provide human-readable functional consequence if p.? or empty
        if not hgvs_p or hgvs_p.strip() == "p.?":
            c_lower = consequence.lower()
            if "splice_donor" in c_lower:
                hgvs_p = "Splice Donor (p.?)"
            elif "splice_acceptor" in c_lower:
                hgvs_p = "Splice Acceptor (p.?)"
            elif "splice_region" in c_lower:
                hgvs_p = "Splice Region (p.?)"
            elif "upstream" in c_lower or "5_prime_utr" in c_lower:
                hgvs_p = "Promoter / 5' UTR (p.?)"
            elif "synonymous" in c_lower:
                hgvs_p = "p.(=) Synonymous"
            elif "intron" in c_lower:
                hgvs_p = "Intronic (p.?)"
            elif "stop_gained" in c_lower:
                hgvs_p = "p.Ter (Stop Gained)"
            elif "frameshift" in c_lower:
                hgvs_p = "Frameshift (p.?)"
            elif "inframe" in c_lower:
                hgvs_p = "In-frame (p.?)"
            elif hgvs_c:
                hgvs_p = f"{consequence.replace('_', ' ').title()}"

        # Build candidate object
        variant_candidate = {
            "case_id": case_id,
            "chrom": chrom,
            "pos": pos,
            "ref": ref,
            "alt": alt_str,
            "qual": qual,
            "filter": filt,
            "genotype": gt,
            "depth": depth,
            "alt_depth": alt_depth,
            "vaf": vaf,
            "phase_set": phase_set,
            "haplotype": haplotype,
            "gene_symbol": gene_symbol,
            "transcript_id": transcript_id,
            "hgvs_c": hgvs_c,
            "hgvs_p": hgvs_p,
            "consequence": consequence,
            "exon": exon,
            "clinvar_sig": clinvar_sig,
            "clinvar_id": clinvar_id,
            "gnomad_af": gnomad_af,
            "cadd_phred": cadd,
            "revel": revel,
            "spliceai_ds_max": spliceai,
            "review_status": "Unreviewed",
            "tags": "",
            "notes": ""
        }

        # Automated Classification
        acmg_class, criteria, score = classify_variant_acmg(variant_candidate)
        somatic_tier, is_actionable = classify_somatic_tier(variant_candidate)

        variant_candidate["acmg_class"] = acmg_class
        variant_candidate["acmg_criteria"] = ",".join(criteria)
        variant_candidate["acmg_score"] = score
        variant_candidate["somatic_tier"] = somatic_tier
        variant_candidate["is_actionable"] = 1 if is_actionable else 0

        variants.append(variant_candidate)

    return variants
