"""
Comprehensive Unit Tests for the Production Clinical Long-Read Multi-Omics Platform.
Covers:
- Zero-Copy HTTP 206 Streaming (variant_explorer.streamer)
- Tavtigian Bayesian ACMG Classification & Abou Tayoun PVS1 (variant_explorer.acmg_engine)
- Complex SV & BND Fusion Graph (variant_explorer.sv_engine)
- Native 5mC Epigenetics & ASM Imprinting (variant_explorer.methylation_engine)
- Long-Read Physical Phasing & Compound Heterozygosity (variant_explorer.phasing_engine)
- Tandem Repeat Expansions (variant_explorer.tandem_repeats)
- Clinical Diagnostic Report Generator (variant_explorer.report_generator)
"""

import unittest
import os
import json
from variant_explorer.app import create_app
from variant_explorer.streamer import parse_range_header
from variant_explorer.acmg_engine import ACMGEngine
from variant_explorer.sv_engine import SVEngine
from variant_explorer.methylation_engine import MethylationEngine
from variant_explorer.phasing_engine import PhasingEngine
from variant_explorer.tandem_repeats import TandemRepeatEngine
from variant_explorer.report_generator import ClinicalReportGenerator


class TestClinicalLongReadPlatform(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    # -------------------------------------------------------------
    # 1. Zero-Copy HTTP 206 Streaming Tests
    # -------------------------------------------------------------
    def test_parse_range_header(self):
        # Normal range
        self.assertEqual(parse_range_header("bytes=0-49", 100), (0, 49))
        # Open end
        self.assertEqual(parse_range_header("bytes=50-", 100), (50, 99))
        # Suffix range
        self.assertEqual(parse_range_header("bytes=-30", 100), (70, 99))
        # Out of bounds
        self.assertIsNone(parse_range_header("bytes=150-200", 100))
        # Invalid format
        self.assertIsNone(parse_range_header("invalid", 100))

    def test_streaming_api_endpoints(self):
        # Full file (200 OK)
        res = self.client.get("/api/stream/files/example_data/hg002_ont_benchmark/metadata.json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("Accept-Ranges"), "bytes")
        total_len = len(res.data)

        # Partial file via Range header (206 Partial Content)
        res_part = self.client.get(
            "/api/stream/files/example_data/hg002_ont_benchmark/metadata.json",
            headers={"Range": "bytes=0-99"}
        )
        self.assertEqual(res_part.status_code, 206)
        self.assertEqual(len(res_part.data), 100)
        self.assertEqual(res_part.headers.get("Content-Range"), f"bytes 0-99/{total_len}")

    # -------------------------------------------------------------
    # 2. Tavtigian Bayesian ACMG & Abou Tayoun PVS1 Tests
    # -------------------------------------------------------------
    def test_acmg_pvs1_evaluation(self):
        # Frameshift in haploinsufficient BRCA1 -> PVS1_VeryStrong (+8)
        code, pts, desc = ACMGEngine.evaluate_pvs1("BRCA1", "frameshift_variant", "c.3700_3704del", "p.Val1234fs")
        self.assertEqual(code, "PVS1_VeryStrong")
        self.assertEqual(pts, 8)

        # Splice donor in established LoF gene MLH1 -> PVS1_VeryStrong (+8)
        code_sp, pts_sp, _ = ACMGEngine.evaluate_pvs1("MLH1", "splice_donor_variant", "c.677+1G>A", "p.?")
        self.assertEqual(code_sp, "PVS1_VeryStrong")
        self.assertEqual(pts_sp, 8)

    def test_acmg_pejaver_calibrated_in_silico(self):
        # High REVEL score -> PP3_Strong (+4)
        ev = ACMGEngine.evaluate_in_silico(revel=0.950)
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["code"], "PP3_Strong")
        self.assertEqual(ev[0]["points"], 4)

        # Very low REVEL score -> BP4_Strong (-4)
        ev_benign = ACMGEngine.evaluate_in_silico(revel=0.010)
        self.assertEqual(ev_benign[0]["code"], "BP4_Strong")
        self.assertEqual(ev_benign[0]["points"], -4)

    def test_acmg_full_classification(self):
        # Rare pathogenic LoF variant with high REVEL
        var = {
            "gene_symbol": "BRCA1",
            "consequence": "frameshift_variant",
            "hgvs_c": "c.5266dupC",
            "hgvs_p": "p.Gln1756fs",
            "gnomad_af": 0.00001,
            "revel_score": 0.94,
            "clinvar_sig": "Pathogenic"
        }
        res = ACMGEngine.classify(var)
        self.assertEqual(res["classification"], "Pathogenic")
        self.assertGreaterEqual(res["total_points"], 10)
        self.assertIn("PVS1_VeryStrong", res["codes_applied"])

    # -------------------------------------------------------------
    # 3. Structural Variant & BND Fusion Graph Tests
    # -------------------------------------------------------------
    def test_sv_bnd_parsing(self):
        alt = "N[chr22:23290413["
        parsed = SVEngine.parse_bnd_alt(alt)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed[0], "22")
        self.assertEqual(parsed[1], 23290413)

    def test_sv_reciprocal_fusion_grouping(self):
        svs = [
            {
                "id": "bnd_1",
                "sv_type": "BND",
                "chrom": "chr9",
                "start": 130714470,
                "alt": "N[chr22:23290413[",
                "gene_symbol": "ABL1",
                "partner_gene": "BCR",
                "mate_id": "bnd_2",
                "support": 38
            },
            {
                "id": "bnd_2",
                "sv_type": "BND",
                "chrom": "chr22",
                "start": 23290413,
                "alt": "]chr9:130714470]N",
                "gene_symbol": "BCR",
                "partner_gene": "ABL1",
                "mate_id": "bnd_1",
                "support": 42
            }
        ]
        fusions = SVEngine.group_fusion_candidates(svs)
        self.assertEqual(len(fusions), 1)
        self.assertTrue(fusions[0]["is_known_driver"])
        self.assertIn("Philadelphia", fusions[0]["description"])

    # -------------------------------------------------------------
    # 4. Native 5mC Epigenetics & ASM Tests
    # -------------------------------------------------------------
    def test_bedmethyl_line_parsing(self):
        line = "chr11\t2000000\t2000001\tm\t45\t+\t2000000\t2000001\t0,0,0\t32\t87.5\t28\t4\t0\t0\t0\t0\t0"
        parsed = MethylationEngine.parse_bedmethyl_line(line)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["chrom"], "chr11")
        self.assertEqual(parsed["valid_coverage"], 32)
        self.assertEqual(parsed["percent_modified"], 87.5)
        self.assertEqual(parsed["n_modified"], 28)

    def test_asm_imprinting_evaluation(self):
        # Normal Imprinting at H19 (Delta >= 45%)
        normal_asm = MethylationEngine.evaluate_asm("H19", overall_pct=48.0, hp1_pct=88.0, hp2_pct=8.0)
        self.assertEqual(normal_asm["status"], "Normal Imprinted Pattern")
        self.assertEqual(normal_asm["delta_asm"], 80.0)

        # Beckwith-Wiedemann Hypermethylation (Biallelic hypermethylation)
        bws_asm = MethylationEngine.evaluate_asm("H19", overall_pct=85.0, hp1_pct=92.0, hp2_pct=78.0)
        self.assertEqual(bws_asm["status"], "Abnormal Hypermethylation (Loss of Imprinting)")
        self.assertIn("Beckwith-Wiedemann", bws_asm["interpretation"])

    # -------------------------------------------------------------
    # 5. Phasing & Compound Heterozygosity Tests
    # -------------------------------------------------------------
    def test_compound_heterozygosity_cis_vs_trans(self):
        # In-Trans (Opposite haplotypes in DPYD) -> Confirmed Compound Het
        trans_variants = [
            {
                "id": 1,
                "gene_symbol": "DPYD",
                "hgvs_c": "c.1905+1G>A",
                "hgvs_p": "p.?",
                "genotype": "0|1",
                "acmg_class": "Pathogenic",
                "phase_set": 1000
            },
            {
                "id": 2,
                "gene_symbol": "DPYD",
                "hgvs_c": "c.2846A>T",
                "hgvs_p": "p.Asp949Val",
                "genotype": "1|0",
                "acmg_class": "Pathogenic",
                "phase_set": 1000
            }
        ]
        res_trans = PhasingEngine.evaluate_compound_heterozygosity(trans_variants)
        self.assertEqual(len(res_trans), 1)
        self.assertEqual(res_trans[0]["phase_configuration"], "In-Trans (Opposite Haplotypes)")
        self.assertEqual(res_trans[0]["diagnostic_status"], "Pathogenic Biallelic Pair")

        # In-Cis (Same haplotype 0|1 and 0|1) -> Carrier
        cis_variants = [
            {
                "id": 1,
                "gene_symbol": "CFTR",
                "hgvs_c": "c.1521_1523delCTT",
                "hgvs_p": "p.Phe508del",
                "genotype": "0|1",
                "acmg_class": "Pathogenic",
                "phase_set": 2000
            },
            {
                "id": 2,
                "gene_symbol": "CFTR",
                "hgvs_c": "c.1210-12[5]",
                "hgvs_p": "p.(=)",
                "genotype": "0|1",
                "acmg_class": "Likely Pathogenic",
                "phase_set": 2000
            }
        ]
        res_cis = PhasingEngine.evaluate_compound_heterozygosity(cis_variants)
        self.assertEqual(len(res_cis), 1)
        self.assertEqual(res_cis[0]["phase_configuration"], "In-Cis (Same Haplotype)")
        self.assertEqual(res_cis[0]["diagnostic_status"], "Carrier / Non-Diagnostic")

    # -------------------------------------------------------------
    # 6. Tandem Repeat Expansion Tests
    # -------------------------------------------------------------
    def test_tandem_repeats_huntington(self):
        # Normal allele
        norm = TandemRepeatEngine.evaluate_repeat_allele("HTT", 17, 19, "CAG")
        self.assertEqual(norm["status"], "Normal Range")

        # Pathogenic Full Expansion (45 repeats >= 40)
        path = TandemRepeatEngine.evaluate_repeat_allele("HTT", 18, 45, "CAG")
        self.assertEqual(path["status"], "Pathogenic Full Expansion")
        self.assertEqual(path["acmg_class"], "Pathogenic")

    # -------------------------------------------------------------
    # 7. Clinical Report Generator Tests
    # -------------------------------------------------------------
    def test_clinical_report_compilation(self):
        case = {
            "case_id": "HG002-TEST",
            "patient_name": "Test Subject",
            "platform": "ONT PromethION R10.4.1",
            "mean_coverage": 35.0,
            "read_n50": 32000,
            "phase_block_n50": 18000000
        }
        snvs = [{
            "gene_symbol": "BRCA1",
            "chrom": "chr17",
            "pos": 43044295,
            "hgvs_c": "c.5266dupC",
            "hgvs_p": "p.Gln1756fs",
            "consequence": "frameshift_variant",
            "acmg_class": "Pathogenic"
        }]
        svs = [{
            "gene_symbol": "BCR",
            "sv_type": "BND",
            "chrom": "chr22",
            "start": 23290413,
            "end": 23290414,
            "length": 0,
            "support": 45,
            "acmg_class": "Pathogenic",
            "is_known_fusion": True
        }]
        meth = [{
            "gene_symbol": "H19",
            "chrom": "chr11",
            "start": 2000000,
            "end": 2004000,
            "overall_methylation": 88.0,
            "status": "Abnormal Hypermethylation (Loss of Imprinting)",
            "interpretation": "Beckwith-Wiedemann syndrome"
        }]

        report = ClinicalReportGenerator.compile_report_data(case, snvs, svs, meth)
        self.assertIn("ACTIONABLE FINDINGS IDENTIFIED", report["summary_statement"])
        self.assertEqual(len(report["actionable_findings"]["snvs_indels"]), 1)
        self.assertEqual(len(report["actionable_findings"]["structural_variants"]), 1)

        html = ClinicalReportGenerator.render_html_report(report)
        self.assertIn("BRCA1", html)
        self.assertIn("c.5266dupC", html)
        self.assertIn("Beckwith-Wiedemann", html)


if __name__ == "__main__":
    unittest.main()
