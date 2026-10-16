import unittest
import os
from variant_explorer.methylation_parser import parse_bedmethyl_content

class TestMethylationParser(unittest.TestCase):
    def setUp(self):
        self.example_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'example_data', 'clinical_case_01'
        )
        self.bed_path = os.path.join(self.example_dir, 'ont_case01_methylation.bedMethyl')

    def test_parse_bedmethyl(self):
        self.assertTrue(os.path.exists(self.bed_path))
        with open(self.bed_path, 'r', encoding='utf-8') as f:
            regions = parse_bedmethyl_content(f.read(), case_id=1)

        self.assertGreater(len(regions), 0)

        # Check MLH1 hypermethylation
        mlh1 = next((r for r in regions if r.get('gene_symbol') == 'MLH1'), None)
        self.assertIsNotNone(mlh1)
        self.assertGreaterEqual(mlh1['percent_modified'], 75.0)

        # Check H19/IGF2 ASM
        h19 = next((r for r in regions if 'H19' in r.get('gene_symbol', '')), None)
        self.assertIsNotNone(h19)
        self.assertTrue(h19['is_asm'])

if __name__ == '__main__':
    unittest.main()
