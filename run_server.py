#!/usr/bin/env python3
"""
Hospital Clínic de Barcelona - CoreBM Long-Read Variant Explorer
Server Launcher & Auto-Seeder
"""

import os
import sys
import argparse
from variant_explorer.models import init_db, get_db_connection
from variant_explorer.sample_manager import ingest_sample
from variant_explorer.app import create_app

def check_and_seed_database():
    """Ensure database exists and seeds clinical_case_01 and HG002 benchmark data."""
    init_db()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT case_id FROM cases")
    existing_case_ids = {row[0] for row in cursor.fetchall()}

    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Clinical Case 01
    if "ONT-CLIN-2026-0042" not in existing_case_ids:
        print("[*] Seeding benchmark clinical case 01 (ONT-CLIN-2026-0042)...")
        example_case_dir = os.path.join(base_dir, "example_data", "clinical_case_01")
        meta_file = os.path.join(example_case_dir, "metadata.json")
        snv_file = os.path.join(example_case_dir, "ont_case01_small_variants.vcf")
        sv_file = os.path.join(example_case_dir, "ont_case01_structural_variants.vcf")
        meth_file = os.path.join(example_case_dir, "ont_case01_methylation.bedMethyl")
        
        case_id = ingest_sample(
            metadata_path=meta_file if os.path.exists(meta_file) else None,
            snv_vcf_path=snv_file if os.path.exists(snv_file) else None,
            sv_vcf_path=sv_file if os.path.exists(sv_file) else None,
            meth_bed_path=meth_file if os.path.exists(meth_file) else None,
        )
        print(f"[✓] Successfully seeded clinical case 01: ID {case_id}")

    # 2. HG002 Complete Diploid Reference Genome Benchmark (Hansen et al. Cell 2026)
    hg002_dir = os.path.join(base_dir, "example_data", "hg002_ont_benchmark")
    meta_file = os.path.join(hg002_dir, "metadata.json")
    snv_file = os.path.join(hg002_dir, "hg002_ont_small_variants.vcf")
    sv_file = os.path.join(hg002_dir, "hg002_ont_structural_variants.vcf")
    meth_file = os.path.join(hg002_dir, "hg002_ont_methylation.bedMethyl")

    cursor.execute("SELECT id FROM cases WHERE case_id = 'HG002-GIAB-ONT-R10'")
    hg002_row = cursor.fetchone()
    needs_hg002_load = hg002_row is None

    if hg002_row:
        cursor.execute("SELECT COUNT(*) FROM variants_sv WHERE case_id = ?", (hg002_row[0],))
        sv_count = cursor.fetchone()[0]
        if sv_count < 30:
            needs_hg002_load = True

    if needs_hg002_load and os.path.exists(meta_file):
        print("[*] Loading T2T-HG002 Complete Diploid Truth Set Benchmark (Hansen et al. Cell 2026)...")
        case_id = ingest_sample(
            metadata_path=meta_file,
            snv_vcf_path=snv_file if os.path.exists(snv_file) else None,
            sv_vcf_path=sv_file if os.path.exists(sv_file) else None,
            meth_bed_path=meth_file if os.path.exists(meth_file) else None,
            clear_existing=True
        )
        print(f"[✓] Successfully loaded HG002 Complete Diploid Truth Set: ID {case_id}")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM cases")
    total_cases = cursor.fetchone()[0]
    conn.close()
    print(f"[*] Database verified. {total_cases} clinical case(s) loaded.")

def main():
    parser = argparse.ArgumentParser(description="Hospital Clínic CoreBM Variant Explorer")
    parser.add_argument("--host", default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5050, help="Port (default: 5050)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    print("=================================================================")
    print("  🧬 HOSPITAL CLÍNIC BARCELONA - COREBM VARIANT EXPLORER")
    print("  Oxford Nanopore Variant Interpretation & Epigenetics")
    print("=================================================================")
    
    check_and_seed_database()
    
    app = create_app()
    print("\n🚀 Server starting at: http://localhost:" + str(args.port))
    print("   Press CTRL+C to stop.\n")
    
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()