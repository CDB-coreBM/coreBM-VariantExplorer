import os
import io
import gzip
import json
import sqlite3
import tempfile
import unittest

from variant_explorer.app import create_app
from variant_explorer.models import init_db, get_db_connection
from variant_explorer.phasing_engine import PhasingEngine
from variant_explorer.snv_parser import parse_vcf_snv_content
from variant_explorer.methylation_parser import parse_bedmethyl_content

class TestV13AstraRemediations(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp_dir, "test_remediations.db")
        os.environ["VARIANT_EXPLORER_DB"] = self.db_path
        
        self.app = create_app(self.db_path)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        # Create test case
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO cases (case_id, patient_id, patient_name, sample_name, indication, status)
            VALUES ('CASE_ASTRA_01', 'PAT_001', 'Clinical Patient', 'PATIENT_01', 'Cardiomyopathy', 'Active')
        """)
        self.case_id = cur.lastrowid
        conn.commit()
        conn.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def test_strict_query_parameter_validation(self):
        """Verify malformed page, limit, floats, and integers return HTTP 400 instead of 500."""
        # SNV invalid max_gnomad_af
        r = self.client.get(f"/api/variants/snv?case_id={self.case_id}&max_gnomad_af=invalid")
        self.assertEqual(r.status_code, 400)
        data = r.get_json()
        self.assertIn("Invalid max_gnomad_af", data["message"])

        # SNV max_gnomad_af out of bounds (> 1.0)
        r = self.client.get(f"/api/variants/snv?case_id={self.case_id}&max_gnomad_af=1.5")
        self.assertEqual(r.status_code, 400)

        # SNV invalid page
        r = self.client.get(f"/api/variants/snv?case_id={self.case_id}&page=bad")
        self.assertEqual(r.status_code, 400)

        # SNV page < 1
        r = self.client.get(f"/api/variants/snv?case_id={self.case_id}&page=0")
        self.assertEqual(r.status_code, 400)

        # SNV limit out of bounds (> 500)
        r = self.client.get(f"/api/variants/snv?case_id={self.case_id}&limit=999")
        self.assertEqual(r.status_code, 400)

        # SV invalid min_len
        r = self.client.get(f"/api/variants/sv?case_id={self.case_id}&min_len=-50")
        self.assertEqual(r.status_code, 400)

        # SV malformed max_len
        r = self.client.get(f"/api/variants/sv?case_id={self.case_id}&max_len=not_an_int")
        self.assertEqual(r.status_code, 400)

    def test_case_id_resolution_and_non_fallback(self):
        """Verify non-existent case_id returns 404 and does NOT silently default to case 1."""
        # Repeats endpoint without case_id -> 400
        r = self.client.get("/api/repeats")
        self.assertEqual(r.status_code, 400)

        # Repeats with non-existent case -> 404
        r = self.client.get("/api/repeats?case_id=999999")
        self.assertEqual(r.status_code, 404)

        # Phasing compound_het with non-existent case -> 404
        r = self.client.get("/api/phasing/compound_het?case_id=NONEXISTENT_CASE")
        self.assertEqual(r.status_code, 404)

        # IGV tracks with non-existent case -> 404
        r = self.client.get("/api/igv/tracks/coverage?case_id=NONEXISTENT")
        self.assertEqual(r.status_code, 404)

        r = self.client.get("/api/igv/tracks/snv?case_id=NONEXISTENT")
        self.assertEqual(r.status_code, 404)

    def test_gzip_vcf_upload_decompression(self):
        """Verify uploading .vcf.gz with real gzip magic bytes decompresses and ingests."""
        raw_vcf = (
            "##fileformat=VCFv4.2\n"
            "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n"
            "chr17\t7674220\t.\tC\tT\t60\tPASS\tGENE=TP53;CLNSIG=Pathogenic\tGT:DP:AD:AF:PS\t0|1:40:20,20:0.5:1000\n"
        ).encode("utf-8")
        
        gzipped_vcf = gzip.compress(raw_vcf)
        
        data = {
            "file": (io.BytesIO(gzipped_vcf), "test_sample.vcf.gz"),
            "file_type": "snv_vcf"
        }
        res = self.client.post(
            f"/api/cases/{self.case_id}/upload",
            data=data,
            content_type="multipart/form-data"
        )
        self.assertEqual(res.status_code, 200)
        res_json = res.get_json()
        self.assertEqual(res_json["status"], "success")
        self.assertEqual(res_json["count"], 1)

        # Verify variant is present in SNV query
        q_res = self.client.get(f"/api/variants/snv?case_id={self.case_id}")
        self.assertEqual(q_res.status_code, 200)
        q_data = q_res.get_json()
        self.assertEqual(q_data["total_records"], 1)
        self.assertEqual(q_data["variants"][0]["gene_symbol"], "TP53")
        self.assertEqual(q_data["variants"][0]["phase_set"], "1000")

    def test_vus_pair_in_trans_classified_non_diagnostic(self):
        """Verify two VUS variants in trans are NOT called Pathogenic Biallelic Pair."""
        vus_variants = [
            {
                "id": 1,
                "gene_symbol": "ABCA4",
                "chrom": "chr1",
                "hgvs_c": "c.100A>G",
                "hgvs_p": "p.Thr34Ala",
                "genotype": "0|1",
                "acmg_class": "VUS",
                "phase_set": "5000"
            },
            {
                "id": 2,
                "gene_symbol": "ABCA4",
                "chrom": "chr1",
                "hgvs_c": "c.200C>T",
                "hgvs_p": "p.Pro67Leu",
                "genotype": "1|0",
                "acmg_class": "VUS",
                "phase_set": "5000"
            }
        ]
        res = PhasingEngine.evaluate_compound_heterozygosity(vus_variants)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["phase_configuration"], "In-Trans (Opposite Haplotypes)")
        self.assertEqual(res[0]["diagnostic_status"], "VUS Pair in Trans (Non-Diagnostic)")
        self.assertIn("does not establish pathogenicity", res[0]["clinical_interpretation"])

    def test_unphased_genotype_does_not_call_trans(self):
        """Verify unphased '0/1' and '1/0' genotypes (slash delimiter) cannot be asserted in-trans."""
        unphased_variants = [
            {
                "id": 1,
                "gene_symbol": "DPYD",
                "chrom": "chr1",
                "genotype": "0/1",
                "acmg_class": "Pathogenic",
                "phase_set": "1000"
            },
            {
                "id": 2,
                "gene_symbol": "DPYD",
                "chrom": "chr1",
                "genotype": "1/0",
                "acmg_class": "Pathogenic",
                "phase_set": "1000"
            }
        ]
        res = PhasingEngine.evaluate_compound_heterozygosity(unphased_variants)
        self.assertEqual(len(res), 1)
        self.assertIn("Unphased", res[0]["phase_configuration"])
        self.assertNotEqual(res[0]["diagnostic_status"], "Pathogenic Biallelic Pair")

    def test_sample_isolation_no_hg002_fallback_for_clinical_patient(self):
        """Verify clinical case without BAM registration never falls back to HG002 BAM."""
        r = self.client.get(f"/api/igv/config?case_id={self.case_id}&gene=TP53")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        config = data.get("config", data)
        tracks = config.get("tracks", [])
        
        # Check alignment track does NOT point to HG002
        for t in tracks:
            if t.get("type") == "alignment":
                self.assertNotIn("HG002", t.get("url", ""))

if __name__ == "__main__":
    unittest.main()
