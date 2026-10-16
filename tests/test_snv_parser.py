import unittest
import os
from variant_explorer.snv_parser import parse_vcf_snv_content

class TestSnvParser(unittest.TestCase):
    def setUp(self):
        self.example_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'example_data', 'clinical_case_01'
        )
        self.vcf_path = os.path.join(self.example_dir, 'ont_case01_small_variants.vcf')

    def test_parse_snv_vcf(self):
        self.assertTrue(os.path.exists(self.vcf_path))
        with open(self.vcf_path, 'r', encoding='utf-8') as f:
            variants = parse_vcf_snv_content(f.read(), case_id=1)

        self.assertGreater(len(variants), 0)

        # Check TP53 variant
        tp53 = next((v for v in variants if v.get('gene_symbol') == 'TP53'), None)
        self.assertIsNotNone(tp53)
        self.assertEqual(tp53['chrom'], 'chr17')
        self.assertEqual(tp53['pos'], 7674220)
        self.assertEqual(tp53['ref'], 'G')
        self.assertEqual(tp53['alt'], 'A')
        self.assertAlmostEqual(tp53['vaf'], 0.48, places=2)
        self.assertEqual(tp53['phase_set'], '7670000')
        self.assertIn(tp53['acmg_class'], ['Pathogenic', 'Likely Pathogenic'])

    def test_phased_status(self):
        with open(self.vcf_path, 'r', encoding='utf-8') as f:
            variants = parse_vcf_snv_content(f.read(), case_id=1)
        phased_count = sum(1 for v in variants if v.get('phase_set') is not None)
        self.assertGreater(phased_count, 0)

if __name__ == '__main__':
    unittest.main()
