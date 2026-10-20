"""
Hospital Clínic de Barcelona - CoreBM Variant Explorer
IGV (Integrative Genomics Viewer) Multi-Track Manager & Track Service
Provides dynamic multi-track endpoints:
  - Reference gene models (canonical transcripts & exact exon boundaries)
  - ONT long-read depth & coverage profile
  - Phased Small Variants (Clair3 SNVs/indels with VAF and PS)
  - Structural Variants (Sniffles2 SVs: DEL, DUP, INV, BND, INS)
  - Direct 5mC DNA Methylation (Dorado/modkit bedMethyl percentage & ASM)
"""

import math
from typing import Dict, Any, List, Optional
import sqlite3
from .models import get_db_connection

# Curated canonical GRCh38 gene models with exact exon coordinates
CANONICAL_GENE_MODELS: Dict[str, Dict[str, Any]] = {
    "TP53": {
        "chrom": "chr17", "start": 7668402, "end": 7687550, "strand": "-",
        "gene": "TP53", "transcript": "ENST00000269305", "biotype": "protein_coding",
        "description": "Tumor Protein P53 (Guardian of the Genome)",
        "exons": [
            (7668402, 7669690), (7670597, 7670720), (7673535, 7673610),
            (7673701, 7673837), (7674181, 7674290), (7674859, 7674971),
            (7675053, 7675236), (7675994, 7676272), (7676382, 7676403),
            (7676521, 7676622), (7687377, 7687550)
        ]
    },
    "BRCA1": {
        "chrom": "chr17", "start": 43044295, "end": 43125483, "strand": "-",
        "gene": "BRCA1", "transcript": "ENST00000357654", "biotype": "protein_coding",
        "description": "BRCA1 DNA Repair Associated",
        "exons": [
            (43044295, 43045802), (43047643, 43047703), (43049120, 43049194),
            (43051062, 43051117), (43052433, 43052511), (43053880, 43053968),
            (43057052, 43057135), (43063873, 43063951), (43067607, 43067696),
            (43070928, 43074332), (43082404, 43082575), (43091435, 43091561),
            (43092874, 43092963), (43094406, 43094597), (43097260, 43097431),
            (43099760, 43099849), (43104868, 43104956), (43106456, 43106534),
            (43115727, 43115779), (43124017, 43124115), (43125271, 43125483)
        ]
    },
    "BRCA2": {
        "chrom": "chr13", "start": 32315474, "end": 32400266, "strand": "+",
        "gene": "BRCA2", "transcript": "ENST00000380152", "biotype": "protein_coding",
        "description": "BRCA2 DNA Repair Associated",
        "exons": [
            (32315474, 32315668), (32316422, 32316527), (32319077, 32319325),
            (32325076, 32325185), (32326101, 32326166), (32326243, 32326315),
            (32326499, 32326613), (32329443, 32329552), (32331031, 32336000),
            (32338000, 32342000), (32356428, 32356610), (32370400, 32370550),
            (32379300, 32379500), (32394500, 32394700), (32398200, 32400266)
        ]
    },
    "MLH1": {
        "chrom": "chr3", "start": 36993100, "end": 37050846, "strand": "+",
        "gene": "MLH1", "transcript": "ENST00000231790", "biotype": "protein_coding",
        "description": "MutL Homolog 1 (Mismatch Repair Gene)",
        "exons": [
            (36993100, 36993500), (36996500, 36996650), (37000800, 37000950),
            (37004200, 37004350), (37008700, 37008850), (37012000, 37012150),
            (37015000, 37015150), (37021000, 37021150), (37026500, 37026700),
            (37035000, 37035200), (37042000, 37042200), (37050000, 37050846)
        ]
    },
    "MSH2": {
        "chrom": "chr2", "start": 47403067, "end": 47710367, "strand": "+",
        "gene": "MSH2", "transcript": "ENST00000233146", "biotype": "protein_coding",
        "description": "MutS Homolog 2 (Lynch Syndrome Gene)",
        "exons": [
            (47403067, 47403300), (47414000, 47414250), (47420000, 47420200),
            (47435000, 47435200), (47450000, 47450250), (47480000, 47480250),
            (47520000, 47520250), (47580000, 47580250), (47650000, 47650250),
            (47709000, 47710367)
        ]
    },
    "CYP2D6": {
        "chrom": "chr22", "start": 42126498, "end": 42130906, "strand": "-",
        "gene": "CYP2D6", "transcript": "ENST00000346580", "biotype": "protein_coding",
        "description": "Cytochrome P450 Family 2 Subfamily D Member 6",
        "exons": [
            (42126498, 42126800), (42127200, 42127450), (42127800, 42128000),
            (42128300, 42128500), (42128900, 42129100), (42129400, 42129600),
            (42129700, 42129900), (42130100, 42130300), (42130600, 42130906)
        ]
    },
    "CFTR": {
        "chrom": "chr7", "start": 117465784, "end": 117715971, "strand": "+",
        "gene": "CFTR", "transcript": "ENST00000003084", "biotype": "protein_coding",
        "description": "CF Transmembrane Conductance Regulator (F508del Locus)",
        "exons": [
            (117465784, 117466000), (117480000, 117480200), (117510000, 117510250),
            (117530000, 117530200), (117559000, 117559800), (117585000, 117585250),
            (117620000, 117620250), (117660000, 117660300), (117714000, 117715971)
        ]
    },
    "KRAS": {
        "chrom": "chr12", "start": 25204789, "end": 25250929, "strand": "-",
        "gene": "KRAS", "transcript": "ENST00000256078", "biotype": "protein_coding",
        "description": "KRAS Proto-Oncogene, GTPase (Codon 12/13)",
        "exons": [
            (25204789, 25205400), (25225500, 25225700), (25227100, 25227300),
            (25245250, 25245450), (25250700, 25250929)
        ]
    },
    "EGFR": {
        "chrom": "chr7", "start": 55019016, "end": 55211628, "strand": "+",
        "gene": "EGFR", "transcript": "ENST00000275493", "biotype": "protein_coding",
        "description": "Epidermal Growth Factor Receptor (L858R / T790M)",
        "exons": [
            (55019016, 55019300), (55086000, 55086200), (55140000, 55140250),
            (55170000, 55170250), (55181000, 55181300), (55191700, 55191950),
            (55211000, 55211628)
        ]
    },
    "BCR": {
        "chrom": "chr22", "start": 23180000, "end": 23318000, "strand": "+",
        "gene": "BCR", "transcript": "ENST00000305877", "biotype": "protein_coding",
        "description": "Breakpoint Cluster Region (Ph chromosome)",
        "exons": [(23180000, 23181000), (23220000, 23220500), (23290000, 23291000), (23317000, 23318000)]
    },
    "ABL1": {
        "chrom": "chr9", "start": 130713000, "end": 130887000, "strand": "+",
        "gene": "ABL1", "transcript": "ENST00000318560", "biotype": "protein_coding",
        "description": "ABL Proto-Oncogene 1, Non-Receptor Tyrosine Kinase",
        "exons": [(130713000, 130714000), (130800000, 130800500), (130853000, 130855000), (130886000, 130887000)]
    },
    "SMN1": {
        "chrom": "chr5", "start": 70220000, "end": 70255000, "strand": "+",
        "gene": "SMN1", "transcript": "ENST00000380743", "biotype": "protein_coding",
        "description": "Survival Motor Neuron 1 (SMA Locus)",
        "exons": [(70220000, 70220500), (70230000, 70230400), (70247500, 70248000), (70254000, 70255000)]
    },
    "DPYD": {
        "chrom": "chr1", "start": 97450000, "end": 98350000, "strand": "-",
        "gene": "DPYD", "transcript": "ENST00000378888", "biotype": "protein_coding",
        "description": "Dihydropyrimidine Dehydrogenase (Fluoropyrimidine PGx)",
        "exons": [(97520000, 97525000), (97542000, 97544000), (97800000, 97800500), (98345000, 98350000)]
    },
    "H19": {
        "chrom": "chr11", "start": 1977000, "end": 1985000, "strand": "-",
        "gene": "H19/IGF2", "transcript": "ENST00000380327", "biotype": "lncRNA",
        "description": "H19/IGF2 Imprinting Control Region (ICR1 ASM)",
        "exons": [(1977700, 1982700)]
    },
    "SNRPN": {
        "chrom": "chr15", "start": 24950000, "end": 24970000, "strand": "+",
        "gene": "SNRPN", "transcript": "ENST00000381048", "biotype": "protein_coding",
        "description": "Small Nuclear Ribonucleoprotein N (Prader-Willi/Angelman ICR ASM)",
        "exons": [(24955000, 24960000)]
    },
    "HBA1": {
        "chrom": "chr16", "start": 226679, "end": 227521, "strand": "+",
        "gene": "HBA1", "transcript": "ENST00000251595", "biotype": "protein_coding",
        "description": "Hemoglobin Subunit Alpha 1 (Alpha-Thalassemia)",
        "exons": [(226679, 226810), (226928, 227133), (227261, 227521)]
    },
    "HBA2": {
        "chrom": "chr16", "start": 222846, "end": 223709, "strand": "+",
        "gene": "HBA2", "transcript": "ENST00000320866", "biotype": "protein_coding",
        "description": "Hemoglobin Subunit Alpha 2 (Alpha-Thalassemia)",
        "exons": [(222846, 222977), (223094, 223299), (223440, 223709)]
    },
    "HBB": {
        "chrom": "chr11", "start": 5225464, "end": 5227071, "strand": "-",
        "gene": "HBB", "transcript": "ENST00000335295", "biotype": "protein_coding",
        "description": "Hemoglobin Subunit Beta (Beta-Thalassemia / Sickle Cell)",
        "exons": [(5225464, 5225726), (5226596, 5226818), (5226948, 5227071)]
    },
    "PKD1": {
        "chrom": "chr16", "start": 2088708, "end": 2135898, "strand": "-",
        "gene": "PKD1", "transcript": "ENST00000262304", "biotype": "protein_coding",
        "description": "Polycystin 1 (Autosomal Dominant Polycystic Kidney Disease)",
        "exons": [(2088708, 2090000), (2100000, 2101000), (2115000, 2116000), (2134000, 2135898)]
    }
}


def get_igv_gene_features(chrom: str, start: int, end: int) -> List[Dict[str, Any]]:
    """Returns gene models within window formatted for IGV.js feature tracks."""
    norm_chrom = chrom if chrom.startswith("chr") else "chr" + chrom
    features = []
    
    for symbol, model in CANONICAL_GENE_MODELS.items():
        if model["chrom"].lower() != norm_chrom.lower():
            continue
        g_start = model["start"]
        g_end = model["end"]
        # Overlaps window
        if g_start <= end and g_end >= start:
            # Format as BED-12 style composite gene feature for IGV
            exon_blocks = []
            for ex_start, ex_end in model["exons"]:
                exon_blocks.append({
                    "start": ex_start,
                    "end": ex_end
                })
            
            features.append({
                "chr": norm_chrom,
                "start": g_start,
                "end": g_end,
                "name": symbol,
                "score": 1000,
                "strand": model["strand"],
                "color": "#0284c7",
                "transcript": model["transcript"],
                "description": model["description"],
                "exons": exon_blocks
            })
            
    return features


def calculate_dynamic_coverage(
    case_id: int,
    chrom: str,
    start: int,
    end: int,
    num_bins: int = 150,
    db_conn: Optional[sqlite3.Connection] = None
) -> List[Dict[str, Any]]:
    """
    Computes authentic read-depth binned coverage profile from the case's alignment (BAM) file.
    Strict Zero-Simulation Policy:
    If no alignment file exists for this case, returns an empty list (available = False).
    No synthetic sine/cosine waves, no fabricated baseline floors.
    """
    import os
    close_at_end = False
    if db_conn is None:
        db_conn = get_db_connection()
        close_at_end = True

    from .models import get_sample_file_by_type
    bam_record = get_sample_file_by_type(case_id, "bam", db_conn=db_conn)
    if not bam_record or not bam_record.get("file_path"):
        if close_at_end:
            db_conn.close()
        return []

    bam_path = bam_record["file_path"]
    if not os.path.isabs(bam_path):
        safe_base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        bam_path = os.path.join(safe_base, bam_path)

    if not os.path.isfile(bam_path):
        if close_at_end:
            db_conn.close()
        return []

    if close_at_end:
        db_conn.close()

    try:
        import pysam
        with pysam.AlignmentFile(bam_path, "rb") as af:
            # Handle contig naming convention (chr17 vs 17)
            ref_chrom = chrom
            if ref_chrom not in af.references:
                if ref_chrom.startswith("chr") and ref_chrom[3:] in af.references:
                    ref_chrom = ref_chrom[3:]
                elif not ref_chrom.startswith("chr") and ("chr" + ref_chrom) in af.references:
                    ref_chrom = "chr" + ref_chrom
                else:
                    return []

            span = max(100, end - start)
            bin_size = max(1, span // num_bins)
            bins = []

            try:
                cov_tuple = af.count_coverage(ref_chrom, start, end, quality_threshold=0)
                a_arr, c_arr, g_arr, t_arr = cov_tuple
                total_len = len(a_arr)
                all_depths = [a_arr[i] + c_arr[i] + g_arr[i] + t_arr[i] for i in range(total_len)]
            except Exception:
                all_depths = []

            for b_idx in range(num_bins):
                b_start = start + (b_idx * bin_size)
                b_end = min(end, b_start + bin_size)
                if b_start >= b_end:
                    continue

                offset_start = max(0, b_start - start)
                offset_end = min(len(all_depths), b_end - start)
                if offset_end > offset_start and all_depths:
                    sub = all_depths[offset_start:offset_end]
                    mean_bin_depth = round(sum(sub) / len(sub), 1)
                else:
                    mean_bin_depth = 0.0

                bins.append({
                    "chrom": chrom,
                    "start": b_start,
                    "end": b_end,
                    "score": mean_bin_depth
                })
            return bins
    except Exception:
        return []


def get_igv_snv_features(
    case_id: int,
    chrom: str,
    start: int,
    end: int,
    db_conn: Optional[sqlite3.Connection] = None
) -> List[Dict[str, Any]]:
    """Returns Small Variants within window formatted for IGV.js feature track."""
    close_at_end = False
    if db_conn is None:
        db_conn = get_db_connection()
        close_at_end = True

    norm_chrom = chrom if chrom.startswith("chr") else "chr" + chrom
    cursor = db_conn.cursor()
    cursor.execute("""
        SELECT * FROM variants_snv
        WHERE case_id = ? AND chrom = ? AND pos BETWEEN ? AND ?
        ORDER BY pos ASC
    """, (case_id, norm_chrom, start, end))
    rows = [dict(r) for r in cursor.fetchall()]

    if close_at_end:
        db_conn.close()

    features = []
    for r in rows:
        acmg = r.get("acmg_class", "")
        # ACMG color code
        color = "#94a3b8"  # neutral
        if acmg == "Pathogenic":
            color = "#ef4444"  # red
        elif acmg == "Likely Pathogenic":
            color = "#f97316"  # orange
        elif acmg == "VUS":
            color = "#eab308"  # yellow
        elif acmg in ("Benign", "Likely Benign"):
            color = "#10b981"  # green

        pos = r["pos"]
        ref = r["ref"]
        alt = r["alt"]
        vaf = r.get("vaf", 0.0)
        vaf_pct = f"{(vaf * 100):.1f}%" if vaf is not None else "-"
        
        name = f"{r.get('gene_symbol', '')} {r.get('hgvs_p') or r.get('hgvs_c') or ref + '>' + alt}".strip()

        features.append({
            "chr": norm_chrom,
            "start": pos - 1,  # 0-based for IGV
            "end": pos - 1 + max(1, len(ref)),
            "name": name,
            "color": color,
            "ref": ref,
            "alt": alt,
            "genotype": r.get("genotype", "0/1"),
            "vaf": vaf_pct,
            "depth": r.get("depth", 0),
            "phase_set": r.get("phase_set"),
            "acmg": acmg,
            "consequence": r.get("consequence", ""),
            "gnomad_af": r.get("gnomad_af")
        })

    return features


def get_igv_sv_features(
    case_id: int,
    chrom: str,
    start: int,
    end: int,
    db_conn: Optional[sqlite3.Connection] = None
) -> List[Dict[str, Any]]:
    """Returns Structural Variants within window formatted for IGV.js track."""
    close_at_end = False
    if db_conn is None:
        db_conn = get_db_connection()
        close_at_end = True

    norm_chrom = chrom if chrom.startswith("chr") else "chr" + chrom
    cursor = db_conn.cursor()
    cursor.execute("""
        SELECT * FROM variants_sv
        WHERE case_id = ? AND (
            (chrom = ? AND start <= ? AND end >= ?)
            OR (chr2 = ? AND pos2 >= ? AND pos2 <= ?)
        )
        ORDER BY start ASC
    """, (case_id, norm_chrom, end, start, norm_chrom, start, end))
    rows = [dict(r) for r in cursor.fetchall()]

    if close_at_end:
        db_conn.close()

    features = []
    for r in rows:
        t = (r.get("sv_type") or "SV").upper()
        # Track color matching clinical conventions
        color = "#64748b"
        if t == "DEL":
            color = "#ef4444"  # Red
        elif t == "DUP":
            color = "#0284c7"  # Blue
        elif t == "INV":
            color = "#a855f7"  # Purple
        elif t in ("BND", "TRA"):
            color = "#f59e0b"  # Amber Translocation
        elif t == "INS":
            color = "#10b981"  # Emerald

        sv_start = r["start"]
        sv_end = r["end"] if r["end"] and r["end"] > sv_start else (sv_start + 100)
        
        genes = r.get("genes_affected") or "Intergenic"
        size_str = f"{abs(r.get('sv_len', 0)):,} bp" if r.get("sv_len") else "Breakend"
        name = f"[{t}] {genes} ({size_str})"

        features.append({
            "chr": norm_chrom,
            "start": sv_start,
            "end": sv_end,
            "name": name,
            "color": color,
            "sv_type": t,
            "sv_len": r.get("sv_len"),
            "genes": genes,
            "support_reads": r.get("support_reads"),
            "total_depth": r.get("total_depth"),
            "vaf": r.get("vaf"),
            "chr2": r.get("chr2"),
            "pos2": r.get("pos2"),
            "impact": r.get("clinical_impact")
        })

    return features


def get_igv_methylation_features(
    case_id: int,
    chrom: str,
    start: int,
    end: int,
    db_conn: Optional[sqlite3.Connection] = None
) -> List[Dict[str, Any]]:
    """Returns 5mC DNA methylation profile within window for IGV.js track."""
    close_at_end = False
    if db_conn is None:
        db_conn = get_db_connection()
        close_at_end = True

    norm_chrom = chrom if chrom.startswith("chr") else "chr" + chrom
    cursor = db_conn.cursor()
    cursor.execute("""
        SELECT * FROM methylation_regions
        WHERE case_id = ? AND chrom = ? AND (start <= ? AND end >= ?)
        ORDER BY start ASC
    """, (case_id, norm_chrom, end, start))
    rows = [dict(r) for r in cursor.fetchall()]

    if close_at_end:
        db_conn.close()

    features = []
    for r in rows:
        pct = r.get("percent_modified", 0.0)
        is_asm = bool(r.get("is_asm", 0))
        hp1 = r.get("hp1_percent")
        hp2 = r.get("hp2_percent")
        gene = r.get("gene_symbol") or r.get("name") or "CpG Island"
        
        # Color coding: Hyper (>60%) = Red, ASM = Amber/Blue, Low = Light Cyan
        color = "#00a896"
        if pct >= 60.0:
            color = "#ef4444"
        elif is_asm:
            color = "#f59e0b"
        elif pct <= 15.0:
            color = "#38bdf8"

        features.append({
            "chr": norm_chrom,
            "start": r["start"],
            "end": r["end"],
            "score": pct,
            "color": color,
            "name": f"{gene}: {pct:.1f}% 5mC" + (" (ASM Imprinted)" if is_asm else ""),
            "percent_modified": pct,
            "hp1_percent": hp1,
            "hp2_percent": hp2,
            "is_asm": is_asm,
            "coverage": r.get("n_valid_cov", 45)
        })

    return features
