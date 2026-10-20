"""Database models, migrations, and connection helpers for Variant Explorer."""

import sqlite3
import os
import json
from typing import Optional, List, Dict, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "variant_explorer.db")


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Returns an optimized SQLite connection with dictionary row access and WAL mode."""
    target_path = db_path or os.environ.get("VARIANT_EXPLORER_DB", DEFAULT_DB_PATH)
    conn = sqlite3.connect(target_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA cache_size = -64000;")  # 64MB cache
    return conn


def init_db(db_path: Optional[str] = None):
    """Initializes schema and tables for clinical cases, SNVs, SVs, methylation, and reports."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 1. Cases / Patients metadata
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL UNIQUE,
            patient_id TEXT NOT NULL,
            patient_name TEXT NOT NULL,
            dob TEXT,
            gender TEXT,
            sample_name TEXT NOT NULL,
            sample_type TEXT DEFAULT 'Blood / cfDNA',
            indication TEXT,
            sequencing_tech TEXT DEFAULT 'Oxford Nanopore (ONT)',
            platform TEXT DEFAULT 'PromethION 24',
            flowcell_type TEXT DEFAULT 'R10.4.1',
            kit TEXT DEFAULT 'SQK-NBD114.24',
            basecaller TEXT DEFAULT 'Dorado 1.0 (sup,5mCG_5hmCG)',
            alignment_ref TEXT DEFAULT 'GRCh38 / hg38',
            total_reads INTEGER DEFAULT 0,
            mean_depth REAL DEFAULT 0.0,
            n50 INTEGER DEFAULT 0,
            q_score REAL DEFAULT 0.0,
            ti_tv_ratio REAL DEFAULT 0.0,
            notes TEXT,
            status TEXT DEFAULT 'Ready',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Small Variants (SNVs & Indels) from Clair3 / DeepVariant
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS variants_snv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            chrom TEXT NOT NULL,
            pos INTEGER NOT NULL,
            ref TEXT NOT NULL,
            alt TEXT NOT NULL,
            qual REAL DEFAULT 0.0,
            filter TEXT DEFAULT 'PASS',
            genotype TEXT DEFAULT '0/1',
            depth INTEGER DEFAULT 0,
            alt_depth INTEGER DEFAULT 0,
            vaf REAL DEFAULT 0.0,
            phase_set TEXT,
            haplotype INTEGER,
            gene_symbol TEXT,
            transcript_id TEXT,
            hgvs_c TEXT,
            hgvs_p TEXT,
            consequence TEXT,
            exon TEXT,
            clinvar_sig TEXT,
            clinvar_id TEXT,
            gnomad_af REAL DEFAULT 0.0,
            cadd_phred REAL DEFAULT 0.0,
            revel REAL DEFAULT 0.0,
            spliceai_ds_max REAL DEFAULT 0.0,
            acmg_class TEXT DEFAULT 'VUS',
            acmg_criteria TEXT,
            acmg_score INTEGER DEFAULT 0,
            somatic_tier TEXT,
            is_actionable INTEGER DEFAULT 0,
            review_status TEXT DEFAULT 'Unreviewed',
            tags TEXT,
            notes TEXT,
            FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
        )
    """)

    # 3. Structural Variants (>=50bp) from Sniffles2 / cuteSV / Severus
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS variants_sv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            chrom TEXT NOT NULL,
            start INTEGER NOT NULL,
            end INTEGER NOT NULL,
            sv_type TEXT NOT NULL,
            sv_len INTEGER DEFAULT 0,
            qual REAL DEFAULT 0.0,
            filter TEXT DEFAULT 'PASS',
            genotype TEXT DEFAULT '0/1',
            support_reads INTEGER DEFAULT 0,
            total_depth INTEGER DEFAULT 0,
            vaf REAL DEFAULT 0.0,
            tandem_repeat INTEGER DEFAULT 0,
            tr_bed_hit TEXT,
            chr2 TEXT,
            pos2 INTEGER,
            strands TEXT,
            genes_affected TEXT,
            exon_overlap TEXT,
            cytoband TEXT,
            acmg_sv_class TEXT DEFAULT 'VUS',
            clinical_impact TEXT,
            review_status TEXT DEFAULT 'Unreviewed',
            notes TEXT,
            FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
        )
    """)

    # 4. Epigenetic Methylation Regions (from modkit bedMethyl / DMR)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS methylation_regions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            chrom TEXT NOT NULL,
            start INTEGER NOT NULL,
            end INTEGER NOT NULL,
            name TEXT,
            region_type TEXT DEFAULT 'cpg_island',
            gene_symbol TEXT,
            n_valid_cov INTEGER DEFAULT 0,
            percent_modified REAL DEFAULT 0.0,
            n_mod INTEGER DEFAULT 0,
            n_canonical INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Normal',
            hp1_percent REAL,
            hp2_percent REAL,
            is_asm INTEGER DEFAULT 0,
            clinical_significance TEXT,
            notes TEXT,
            FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
        )
    """)

    # 5. Clinical Diagnostic Reports
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clinical_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            report_id TEXT NOT NULL UNIQUE,
            patient_name TEXT NOT NULL,
            indication TEXT,
            summary_text TEXT,
            primary_findings_json TEXT,
            secondary_findings_json TEXT,
            recommendations TEXT,
            signed_by TEXT,
            signed_at TIMESTAMP,
            status TEXT DEFAULT 'Draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
        )
    """)

    # 5b. Persistent Clinical Report Findings (Long-Term Case Variant Curation)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS case_report_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            finding_type TEXT NOT NULL, -- 'SNV', 'SV', 'METHYLATION', 'REPEAT'
            variant_id TEXT NOT NULL,
            gene_symbol TEXT,
            chrom TEXT,
            pos INTEGER,
            ref TEXT,
            alt TEXT,
            acmg_class TEXT,
            somatic_tier TEXT,
            clinical_notes TEXT,
            finding_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE,
            UNIQUE (case_id, finding_type, variant_id)
        )
    """)

    # 5c. Tandem Repeat Expansions (TRGT / Straglr Assay)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tandem_repeats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            gene_symbol TEXT NOT NULL,
            disease TEXT,
            motif TEXT,
            chrom TEXT,
            start INTEGER,
            end INTEGER,
            allele_1_count INTEGER,
            allele_2_count INTEGER,
            status TEXT,
            clinical_significance TEXT,
            acmg_class TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
        )
    """)

    # 6. Gene Panels and Versioned Gene Lists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gene_panels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'Clinical Genetics',
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gene_panel_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            panel_id INTEGER NOT NULL,
            version_str TEXT NOT NULL,
            gene_list_json TEXT NOT NULL,
            gene_count INTEGER NOT NULL,
            changelog TEXT,
            author TEXT DEFAULT 'Hospital Clinic Molecular Genetics',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (panel_id) REFERENCES gene_panels (id) ON DELETE CASCADE
        )
    """)

    # 7. Sample Files Registry (BAM, CRAM, VCF, BedMethyl)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sample_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            sample_name TEXT,
            analysis_type TEXT DEFAULT 'WGS',
            assembly TEXT DEFAULT 'GRCh38',
            file_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            index_path TEXT,
            checksum TEXT,
            is_available INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sample_files_case_type ON sample_files(case_id, file_type);")

    # Indexes for sub-second filtering across millions of records
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_snv_case_pos ON variants_snv (case_id, chrom, pos)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_snv_case_gene ON variants_snv (case_id, gene_symbol)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_snv_case_gene_nocase ON variants_snv (case_id, gene_symbol COLLATE NOCASE)")
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_snv_case_acmg_priority ON variants_snv (
            case_id, 
            CASE acmg_class 
                WHEN 'Pathogenic' THEN 1 
                WHEN 'Likely Pathogenic' THEN 2 
                WHEN 'VUS' THEN 3 
                WHEN 'Likely Benign' THEN 4 
                ELSE 5 
            END ASC, 
            qual DESC
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_snv_case_acmg ON variants_snv (case_id, acmg_class)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_snv_case_vaf ON variants_snv (case_id, vaf)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sv_case_type ON variants_sv (case_id, sv_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sv_case_len ON variants_sv (case_id, sv_len)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_meth_case_gene ON methylation_regions (case_id, gene_symbol)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_meth_case_status ON methylation_regions (case_id, status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_panel_code ON gene_panels (code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_panel_version ON gene_panel_versions (panel_id, is_active)")

    seed_default_gene_panels(conn)

    conn.commit()
    conn.close()


def seed_default_gene_panels(conn: sqlite3.Connection):
    """Seeds standardized clinical gene panels if not already present."""
    import json
    cursor = conn.cursor()

    panels_to_seed = [
        {
            "code": "ACMG_SF_V3_2",
            "name": "ACMG Secondary Findings v3.2 (81 Genes)",
            "category": "Actionable Secondary Findings",
            "description": "American College of Medical Genetics and Genomics recommendations for reporting of secondary findings in clinical exome and genome sequencing (Miller et al. 2023).",
            "version": "v3.2",
            "changelog": "Standard ACMG SF v3.2 81 curated actionable medical genes.",
            "genes": [
                "BRCA1", "BRCA2", "PALB2", "TP53", "PTEN", "MLH1", "MSH2", "MSH6", "PMS2", "APC",
                "MUTYH", "RET", "RB1", "MEN1", "VHL", "WT1", "NF2", "TSC1", "TSC2", "CDH1",
                "STK11", "BMPR1A", "SMAD4", "LDLR", "APOB", "PCSK9", "MYH7", "MYBPC3", "TNNT2", "TNNI3",
                "TPM1", "MYL2", "MYL3", "ACTC1", "PRKAG2", "GLA", "LAMP2", "LMNA", "TTN", "FLNC",
                "DSP", "PKP2", "DSG2", "DSC2", "JUP", "TMEM43", "PLN", "RYR2", "CASQ2", "TRDN",
                "KCNQ1", "KCNH2", "SCN5A", "TGFBR1", "TGFBR2", "SMAD3", "FBN1", "ACTA2", "MYH11", "COL3A1",
                "OTC", "GAA", "ATP7B", "HFE", "TTR", "BTD", "RPE65", "HNF1A", "MAX", "TMEM127",
                "SDHA", "SDHB", "SDHC", "SDHD", "VCL", "DES", "BAG3", "TNNC1", "RBM20", "CALM1", "CALM2"
            ]
        },
        {
            "code": "HBOC_LYNCH",
            "name": "Hereditary Cancer & Lynch Syndrome (24 Genes)",
            "category": "Hereditary Oncology",
            "description": "High and moderate penetrance genes associated with hereditary breast, ovarian, colorectal, and endometrial cancer predisposition.",
            "version": "v1.0",
            "changelog": "Core clinical diagnostic panel for HBOC, Lynch, and polyposis syndromes.",
            "genes": [
                "BRCA1", "BRCA2", "PALB2", "TP53", "CHEK2", "ATM", "BARD1", "BRIP1", "RAD51C", "RAD51D",
                "CDH1", "PTEN", "STK11", "MLH1", "MSH2", "MSH6", "PMS2", "EPCAM", "MUTYH", "NBN",
                "NF1", "RAD50", "SMARCA4", "POLE"
            ]
        },
        {
            "code": "THAL_GLOBIN",
            "name": "Thalassemia & Globin Disorders (12 Genes)",
            "category": "Hematology & Hemoglobinopathies",
            "description": "Genes involved in alpha and beta globin cluster biology, structural hemoglobin variants, and modifier loci.",
            "version": "v1.0",
            "changelog": "Includes HBA1, HBA2 duplicated clusters and HBB locus.",
            "genes": [
                "HBA1", "HBA2", "HBB", "HBD", "HBG1", "HBG2", "HBE1", "HBZ", "BCL11A", "KLF1", "GATA1", "AHSP"
            ]
        },
        {
            "code": "CARDIOMYOPATHY",
            "name": "Cardiomyopathy & Channelopathy (25 Genes)",
            "category": "Cardiology",
            "description": "Hypertrophic, dilated, and arrhythmogenic cardiomyopathy genes plus long-QT/Brugada channels.",
            "version": "v1.0",
            "changelog": "Curated ClinGen definitive and strong evidence cardiomyopathy genes.",
            "genes": [
                "MYH7", "MYBPC3", "TNNT2", "TNNI3", "TPM1", "ACTC1", "LMNA", "PLN", "TTN", "DSP",
                "PKP2", "DSG2", "DSC2", "SCN5A", "KCNQ1", "KCNH2", "RYR2", "FLNC", "RBM20", "BAG3",
                "DES", "VCL", "MYL2", "MYL3", "GLA"
            ]
        },
        {
            "code": "PGX_CPIC",
            "name": "Pharmacogenomics CPIC Tier 1 (16 Genes)",
            "category": "Pharmacogenomics",
            "description": "Clinical Pharmacogenetics Implementation Consortium (CPIC) Level A/B genes with actionable prescribing guidelines.",
            "version": "v1.0",
            "changelog": "Tier 1 pharmacogenes including CYP2D6, DPYD, TPMT, and NUDT15.",
            "genes": [
                "CYP2D6", "CYP2C19", "CYP2C9", "CYP3A5", "CYP2B6", "DPYD", "TPMT", "NUDT15",
                "SLCO1B1", "VKORC1", "UGT1A1", "HLA-A", "HLA-B", "G6PD", "CACNA1S", "RYR1"
            ]
        },
        {
            "code": "CMRG_TIER1",
            "name": "Challenging Medical Genes (CMRG Tier 1)",
            "category": "Medical Genome Benchmarks",
            "description": "GIAB Challenging Medically Relevant Genes resolved with long reads (homologous, repetitive, and pseudogene-adjacent loci).",
            "version": "v1.0",
            "changelog": "GIAB CMRG benchmark loci requiring long-read resolution.",
            "genes": [
                "SMN1", "SMN2", "CYP2D6", "HBA1", "HBA2", "GBA1", "PMS2", "STRC", "OTOA", "NEB",
                "CBS", "F8", "PKD1", "TNXB", "PRSS1", "KMT2C", "KMT2D", "ARX", "FANCD2", "IKBKG", "HYDIN"
            ]
        }
    ]

    for p in panels_to_seed:
        cursor.execute("SELECT id FROM gene_panels WHERE code = ?", (p["code"],))
        existing = cursor.fetchone()
        if not existing:
            cursor.execute("""
                INSERT INTO gene_panels (code, name, category, description)
                VALUES (?, ?, ?, ?)
            """, (p["code"], p["name"], p["category"], p["description"]))
            panel_id = cursor.lastrowid
            genes_json = json.dumps(sorted(list(set(g.upper() for g in p["genes"]))))
            cursor.execute("""
                INSERT INTO gene_panel_versions (panel_id, version_str, gene_list_json, gene_count, changelog, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (panel_id, p["version"], genes_json, len(p["genes"]), p["changelog"]))

    # Seed HG002 sample files if case HG002-GIAB-ONT-R10 exists
    cursor.execute("SELECT id FROM cases WHERE case_id = 'HG002-GIAB-ONT-R10'")
    hg002_case = cursor.fetchone()
    if hg002_case:
        hg002_id = hg002_case["id"]
        cursor.execute("SELECT COUNT(*) FROM sample_files WHERE case_id = ?", (hg002_id,))
        if cursor.fetchone()[0] == 0:
            hg002_files = [
                ("bam", "data_store/samples/HG002/HG002_phased.bam", "data_store/samples/HG002/HG002_phased.bam.bai"),
                ("coverage_bedgraph", "data_store/samples/HG002/HG002_coverage.bedgraph.gz", "data_store/samples/HG002/HG002_coverage.bedgraph.gz.tbi"),
                ("snv_vcf", "data_store/samples/HG002/HG002_CMRG_smallvar.vcf.gz", "data_store/samples/HG002/HG002_CMRG_smallvar.vcf.gz.tbi"),
                ("sv_vcf", "data_store/samples/HG002/HG002_CMRG_SV.vcf.gz", "data_store/samples/HG002/HG002_CMRG_SV.vcf.gz.tbi"),
                ("methylation_bed", "data_store/samples/HG002/hg002_methylation.bed.gz", "data_store/samples/HG002/hg002_methylation.bed.gz.tbi")
            ]
            for ftype, fpath, ipath in hg002_files:
                cursor.execute("""
                    INSERT INTO sample_files (case_id, sample_name, analysis_type, assembly, file_type, file_path, index_path)
                    VALUES (?, 'HG002', 'CMRG_Benchmark', 'GRCh38', ?, ?, ?)
                """, (hg002_id, ftype, fpath, ipath))

    conn.commit()


def get_sample_files(case_id: int, db_conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Returns registered files for a given case."""
    should_close = False
    if db_conn is None:
        db_conn = get_db_connection()
        should_close = True
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM sample_files WHERE case_id = ? AND is_available = 1 ORDER BY id ASC", (case_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    if should_close:
        db_conn.close()
    return rows


def get_sample_file_by_type(case_id: int, file_type: str, db_conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Returns specific file record for a given case and file type."""
    should_close = False
    if db_conn is None:
        db_conn = get_db_connection()
        should_close = True
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM sample_files WHERE case_id = ? AND file_type = ? AND is_available = 1 LIMIT 1", (case_id, file_type))
    row = cursor.fetchone()
    res = dict(row) if row else None
    if should_close:
        db_conn.close()
    return res


def add_sample_file(case_id: int, file_type: str, file_path: str, index_path: Optional[str] = None,
                    sample_name: Optional[str] = None, analysis_type: str = "WGS",
                    assembly: str = "GRCh38", db_conn: Optional[sqlite3.Connection] = None) -> int:
    """Register a genomic file for a case."""
    should_close = False
    if db_conn is None:
        db_conn = get_db_connection()
        should_close = True
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO sample_files (case_id, sample_name, analysis_type, assembly, file_type, file_path, index_path, is_available)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
    """, (case_id, sample_name, analysis_type, assembly, file_type, file_path, index_path))
    db_conn.commit()
    file_id = cursor.lastrowid
    if should_close:
        db_conn.close()
    return file_id


def get_case_report_findings(conn_or_case_id: Any, case_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Retrieve all persistent clinical report findings for a case."""
    if isinstance(conn_or_case_id, int) or (isinstance(conn_or_case_id, str) and str(conn_or_case_id).isdigit()):
        case_id = int(conn_or_case_id)
        conn = get_db_connection()
        should_close = True
    else:
        conn = conn_or_case_id
        should_close = False

    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, case_id, finding_type, variant_id, gene_symbol, chrom, pos,
               ref, alt, acmg_class, somatic_tier, clinical_notes, finding_json, created_at, updated_at
        FROM case_report_findings
        WHERE case_id = ?
        ORDER BY created_at ASC
    """, (case_id,))
    rows = cursor.fetchall()
    results = []
    for r in rows:
        try:
            item = json.loads(r["finding_json"])
        except Exception:
            item = {}
        item["id"] = r["id"]
        item["reportFindingId"] = r["id"]
        item["db_id"] = r["id"]
        item["case_id"] = r["case_id"]
        item["finding_type"] = r["finding_type"]
        item["variant_id"] = r["variant_id"]
        item["gene_symbol"] = r["gene_symbol"] or item.get("gene_symbol")
        item["acmg_class"] = r["acmg_class"] or item.get("acmg_class")
        item["clinical_notes"] = r["clinical_notes"] if r["clinical_notes"] is not None else item.get("clinical_notes", "")
        item["created_at"] = r["created_at"]
        item["isClinicianAdded"] = True
        results.append(item)
    if should_close:
        conn.close()
    return results


def save_case_report_finding(conn: sqlite3.Connection, case_id: int, finding: Dict[str, Any]) -> int:
    """Save or update a persistent clinical report finding for a case."""
    cursor = conn.cursor()
    finding_type = "SNV"
    if finding.get("sv_type"):
        finding_type = "SV"
    elif finding.get("region_type") or "mean_5mc" in finding or "percent_modified" in finding:
        finding_type = "METHYLATION"
    elif finding.get("motif") or "allele_1_count" in finding:
        finding_type = "REPEAT"

    variant_id = str(finding.get("id") or finding.get("variant_id") or finding.get("reportFindingId") or "")
    if not variant_id:
        if finding_type == "SV":
            variant_id = f"sv_{finding.get('chrom')}:{finding.get('start')}-{finding.get('end')}:{finding.get('sv_type')}"
        elif finding_type == "METHYLATION":
            variant_id = f"meth_{finding.get('chrom')}:{finding.get('start')}-{finding.get('end')}:{finding.get('gene_symbol','')}"
        elif finding_type == "REPEAT":
            variant_id = f"rep_{finding.get('gene_symbol')}:{finding.get('motif')}"
        else:
            variant_id = f"snv_{finding.get('chrom')}:{finding.get('pos')}:{finding.get('ref')}>{finding.get('alt')}"

    gene_symbol = finding.get("gene_symbol") or finding.get("genes_affected") or finding.get("gene") or ""
    chrom = finding.get("chrom") or ""
    pos = finding.get("pos") or finding.get("start")
    ref = finding.get("ref") or ""
    alt = finding.get("alt") or ""
    acmg_class = finding.get("acmg_class") or finding.get("clinical_significance") or "Actionable"
    somatic_tier = finding.get("somatic_tier") or ""
    clinical_notes = finding.get("clinical_notes") or finding.get("interpretation") or ""
    finding_json = json.dumps(finding)

    cursor.execute("""
        INSERT INTO case_report_findings (
            case_id, finding_type, variant_id, gene_symbol, chrom, pos,
            ref, alt, acmg_class, somatic_tier, clinical_notes, finding_json, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(case_id, finding_type, variant_id) DO UPDATE SET
            acmg_class = excluded.acmg_class,
            clinical_notes = excluded.clinical_notes,
            finding_json = excluded.finding_json,
            updated_at = CURRENT_TIMESTAMP
    """, (case_id, finding_type, variant_id, gene_symbol, chrom, pos, ref, alt, acmg_class, somatic_tier, clinical_notes, finding_json))
    conn.commit()

    # In SQLite ON CONFLICT DO UPDATE, lastrowid might be 0 if an existing row was updated
    finding_db_id = cursor.lastrowid
    if not finding_db_id or finding_db_id <= 0:
        cursor.execute("SELECT id FROM case_report_findings WHERE case_id = ? AND finding_type = ? AND variant_id = ?",
                       (case_id, finding_type, variant_id))
        row = cursor.fetchone()
        finding_db_id = row[0] if row else None

    return finding_db_id


def delete_case_report_finding(conn_or_case_id: Any, case_id_or_finding_id: Any = None, finding_id: Any = None) -> bool:
    """Delete a report finding by primary ID or variant_id."""
    if finding_id is not None:
        conn = conn_or_case_id
        case_id = case_id_or_finding_id
        fid = finding_id
        should_close = False
    else:
        conn = get_db_connection()
        case_id = conn_or_case_id
        fid = case_id_or_finding_id
        should_close = True

    cursor = conn.cursor()
    if isinstance(fid, int) or (isinstance(fid, str) and str(fid).isdigit()):
        cursor.execute("DELETE FROM case_report_findings WHERE case_id = ? AND id = ?", (case_id, int(fid)))
    else:
        cursor.execute("DELETE FROM case_report_findings WHERE case_id = ? AND variant_id = ?", (case_id, str(fid)))
    conn.commit()
    rc = cursor.rowcount > 0
    if should_close:
        conn.close()
    return rc


def update_case_report_finding_notes(conn: sqlite3.Connection, case_id: int, finding_id: Any,
                                     notes: str, acmg_class: Optional[str] = None) -> bool:
    """Update clinical curation notes or ACMG classification for a saved finding."""
    cursor = conn.cursor()
    is_numeric = isinstance(finding_id, int) or (isinstance(finding_id, str) and str(finding_id).isdigit())
    id_clause = "id = ?" if is_numeric else "variant_id = ?"
    val = int(finding_id) if is_numeric else str(finding_id)

    # First fetch current finding_json to update it synchronously
    cursor.execute(f"SELECT id, finding_json, acmg_class FROM case_report_findings WHERE case_id = ? AND {id_clause}", (case_id, val))
    row = cursor.fetchone()
    if not row:
        return False
    row_id = row[0]
    raw_json = row[1]
    curr_acmg = acmg_class or row[2]
    try:
        data = json.loads(raw_json) if raw_json else {}
    except Exception:
        data = {}
    data["clinical_notes"] = notes
    if acmg_class:
        data["acmg_class"] = acmg_class
    new_json = json.dumps(data)

    if acmg_class:
        cursor.execute("""
            UPDATE case_report_findings 
            SET clinical_notes = ?, acmg_class = ?, finding_json = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (notes, acmg_class, new_json, row_id))
    else:
        cursor.execute("""
            UPDATE case_report_findings 
            SET clinical_notes = ?, finding_json = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (notes, new_json, row_id))
    conn.commit()
    return cursor.rowcount > 0


if __name__ == "__main__":
    init_db()
    print("✓ Variant Explorer database schema initialized successfully.")
