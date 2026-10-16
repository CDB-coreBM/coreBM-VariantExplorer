import unittest
from variant_explorer.acmg_classifier import classify_variant_acmg, classify_somatic_tier

class TestAcmgClassifier(unittest.TestCase):
    def test_pathogenic_frameshift(self):
        v = {
            'consequence': 'frameshift_variant',
            'gene_symbol': 'BRCA1',
            'gnomad_af': 0.00001,
            'clinvar_sig': 'Pathogenic'
        }
        classification, criteria, score = classify_variant_acmg(v)
        self.assertEqual(classification, 'Pathogenic')
        self.assertIn('PVS1', criteria)

    def test_benign_high_af(self):
        v = {
            'consequence': 'missense_variant',
            'gene_symbol': 'TP53',
            'gnomad_af': 0.08 # 8% in population
        }
        classification, criteria, score = classify_variant_acmg(v)
        self.assertEqual(classification, 'Benign')
        self.assertIn('BA1', criteria)

    def test_somatic_tier_1_actionable(self):
        v = {
            'gene_symbol': 'EGFR',
            'hgvs_p': 'p.Leu858R',
            'consequence': 'missense_variant',
            'vaf': 0.50
        }
        tier, is_act = classify_somatic_tier(v)
        self.assertTrue(tier.startswith('Tier I'))
        self.assertTrue(is_act)

if __name__ == '__main__':
    unittest.main()
