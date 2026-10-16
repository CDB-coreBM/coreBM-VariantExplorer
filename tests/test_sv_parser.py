import unittest
import os
from variant_explorer.sv_parser import parse_vcf_sv_content

class TestSvParser(unittest.TestCase):
    def setUp(self):
        self.example_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'example_data', 'clinical_case_01'
        )
        self.vcf_path = os.path.join(self.example_dir, 'ont_case01_structural_variants.vcf')

    def test_parse_sv_vcf(self):
        self.assertTrue(os.path.exists(self.vcf_path))
        with open(self.vcf_path, 'r', encoding='utf-8') as f:
            svs = parse_vcf_sv_content(f.read(), case_id=1)

        self.assertGreaterEqual(len(svs), 4)

        # Check MSH2 deletion
        msh2 = next((s for s in svs if 'MSH2' in s.get('genes_affected', '')), None)
        self.assertIsNotNone(msh2)
        self.assertEqual(msh2['sv_type'], 'DEL')
        self.assertEqual(msh2['sv_len'], 14200)
        self.assertGreater(msh2['support_reads'], 10)

        # Check BCR translocation (BND)
        bcr = next((s for s in svs if s.get('sv_type') == 'BND'), None)
        self.assertIsNotNone(bcr)
        self.assertEqual(bcr['chrom'], 'chr9')
        self.assertEqual(bcr['chr2'], 'chr22')

if __name__ == '__main__':
    unittest.main()
