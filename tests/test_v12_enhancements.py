import unittest
import os
import json
from variant_explorer.app import create_app
from variant_explorer.models import (
    init_db,
    save_case_report_finding,
    get_case_report_findings,
    delete_case_report_finding,
    update_case_report_finding_notes,
)
from variant_explorer.gene_catalog import validate_genes, get_gene_coordinates
from variant_explorer.sample_manager import ingest_sample


class TestV12Enhancements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = create_app()
        app.config['TESTING'] = True
        cls.client = app.test_client()
        init_db()

        base_dir = os.path.dirname(os.path.dirname(__file__))
        example_case_dir = os.path.join(base_dir, 'example_data', 'clinical_case_01')
        meta_file = os.path.join(example_case_dir, 'metadata.json')
        snv_file = os.path.join(example_case_dir, 'ont_case01_small_variants.vcf')
        sv_file = os.path.join(example_case_dir, 'ont_case01_structural_variants.vcf')
        meth_file = os.path.join(example_case_dir, 'ont_case01_methylation.bedMethyl')

        cls.case_id = ingest_sample(
            metadata_path=meta_file,
            snv_vcf_path=snv_file,
            sv_vcf_path=sv_file,
            meth_bed_path=meth_file,
        )

    def test_sv_view_defaults_to_table(self):
        """Verify SV explorer HTML defaults to table section and table button."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('id="svTableSection"', html)
        self.assertIn('id="svCircosSection"', html)
        self.assertIn('id="svCircosSection" class="card" style="display: none;', html)
        self.assertIn('id="svViewTableBtn" class="btn btn-primary"', html)
        self.assertIn('id="svViewCircosBtn" class="btn btn-secondary"', html)

    def test_methylation_view_defaults_to_table(self):
        """Verify Methylation explorer HTML defaults to table section and has switcher."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('id="methTableSection" style="display: block;"', html)
        self.assertIn('id="methStudioSection" class="card" style="display: none;', html)
        self.assertIn('id="methViewTableBtn" class="btn btn-primary"', html)
        self.assertIn('id="methViewStudioBtn" class="btn btn-secondary"', html)

    def test_tandem_repeats_dedicated_view_and_api(self):
        """Verify repeats section in nav and /api/repeats endpoint."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('data-view="repeats-view"', html)
        self.assertIn('id="repeats-view"', html)
        self.assertIn('repeats_view.js', html)

        # Test API
        api_res = self.client.get(f'/api/repeats?case_id={self.case_id}')
        self.assertEqual(api_res.status_code, 200)
        data = json.loads(api_res.data)
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('repeats', data)
        self.assertGreater(len(data['repeats']), 0)
        
        # Verify fields in repeat record
        rep = data['repeats'][0]
        self.assertIn('gene', rep)
        self.assertIn('locus_id', rep)
        self.assertIn('allele1_copies', rep)
        self.assertIn('allele2_copies', rep)
        self.assertIn('expansion_status', rep)

    def test_report_findings_persistence_db_and_api(self):
        """Verify report findings persist in SQLite across restarts and via REST API."""
        finding_payload = {
            "finding_type": "sv",
            "variant_id": "TEST_SV_001",
            "chrom": "chr17",
            "pos": 43044295,
            "ref_allele": "N",
            "alt_allele": "<DEL>",
            "gene_symbol": "BRCA1",
            "hgvsc": "c.4185del",
            "hgvsp": "p.Cys1395*",
            "acmg_class": "Pathogenic",
            "clinical_significance": "Pathogenic (Tier 1)",
            "clinical_notes": "Structural deletion affecting BRCA1 critical zinc-finger domain",
            "zygosity": "Heterozygous",
            "caller": "Sniffles2",
            "filter_status": "PASS",
            "details_json": {"sv_type": "DEL", "sv_len": -1250}
        }

        # 1. POST finding
        post_res = self.client.post(
            f'/api/cases/{self.case_id}/report_findings',
            data=json.dumps(finding_payload),
            content_type='application/json'
        )
        self.assertEqual(post_res.status_code, 200)
        post_data = json.loads(post_res.data)
        self.assertEqual(post_data.get('status'), 'success')
        finding_id = post_data.get('finding_id')
        self.assertIsNotNone(finding_id)

        # 2. GET findings
        get_res = self.client.get(f'/api/cases/{self.case_id}/report_findings')
        self.assertEqual(get_res.status_code, 200)
        get_data = json.loads(get_res.data)
        self.assertEqual(get_data.get('status'), 'success')
        findings = get_data.get('findings', [])
        self.assertTrue(any(f['variant_id'] == 'TEST_SV_001' for f in findings))

        # 3. PUT update notes
        new_notes = "Updated molecular diagnostic notes for clinical sign-off"
        put_res = self.client.put(
            f'/api/cases/{self.case_id}/report_findings/{finding_id}',
            data=json.dumps({"clinical_notes": new_notes}),
            content_type='application/json'
        )
        self.assertEqual(put_res.status_code, 200)

        # Verify updated in DB directly
        db_findings = get_case_report_findings(self.case_id)
        matching = [f for f in db_findings if f['id'] == finding_id]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]['clinical_notes'], new_notes)

        # 4. DELETE finding
        del_res = self.client.delete(f'/api/cases/{self.case_id}/report_findings/{finding_id}')
        self.assertEqual(del_res.status_code, 200)

        db_findings_after = get_case_report_findings(self.case_id)
        self.assertFalse(any(f['id'] == finding_id for f in db_findings_after))

    def test_gene_validation_logic_and_api(self):
        """Verify HGNC gene validation and fuzzy match suggestions."""
        # Known clinical genes
        valid_res = validate_genes(["BRCA1", "TP53", "FXN", "HTT", "DMPK"])
        self.assertTrue(valid_res['is_all_valid'])
        self.assertEqual(valid_res['invalid_count'], 0)
        self.assertEqual(valid_res['valid_count'], 5)

        # Test typo with suggestions
        typo_res = validate_genes(["BRAFF", "TP53", "FXNN"])
        self.assertFalse(typo_res['is_all_valid'])
        self.assertEqual(typo_res['valid_count'], 1)
        self.assertEqual(typo_res['invalid_count'], 2)
        
        # Check suggestions
        inv_map = {item['symbol']: item['suggestions'] for item in typo_res['invalid_genes']}
        self.assertIn('BRAFF', inv_map)
        self.assertIn('BRAF', inv_map['BRAFF'])
        self.assertIn('FXNN', inv_map)
        self.assertIn('FXN', inv_map['FXNN'])

        # Test API endpoint
        api_res = self.client.post(
            '/api/genes/validate',
            data=json.dumps({"genes": "BRCA1, FXN, NONEXISTENTGENE123"}),
            content_type='application/json'
        )
        self.assertEqual(api_res.status_code, 200)
        api_data = json.loads(api_res.data)
        vdata = api_data.get('data') or api_data
        self.assertEqual(vdata['valid_count'], 2)
        self.assertEqual(vdata['invalid_count'], 1)
        self.assertEqual(vdata['invalid_genes'][0]['symbol'], 'NONEXISTENTGENE123')


if __name__ == '__main__':
    unittest.main()
