import unittest
import os
import json
from variant_explorer.app import create_app
from variant_explorer.models import init_db
from variant_explorer.sample_manager import ingest_sample

class TestApiEndpoints(unittest.TestCase):
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
        from variant_explorer.models import add_sample_file
        add_sample_file(
            cls.case_id,
            file_type="bam",
            file_path="data_store/samples/HG002/HG002_phased.bam",
            index_path="data_store/samples/HG002/HG002_phased.bam.bai",
            sample_name="Case01-ONT"
        )

    def test_index_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Hospital', html)

    def test_get_cases(self):
        response = self.client.get('/api/cases')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('cases', data)
        self.assertGreater(len(data['cases']), 0)

    def test_get_case_detail(self):
        response = self.client.get(f'/api/cases/{self.case_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue('case' in data or ('data' in data and 'case' in data['data']))

    def test_get_snvs(self):
        response = self.client.get(f'/api/variants/snv?case_id={self.case_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('variants', data)
        self.assertGreater(len(data['variants']), 0)

    def test_get_svs(self):
        response = self.client.get(f'/api/variants/sv?case_id={self.case_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('structural_variants', data)
        self.assertGreater(len(data['structural_variants']), 0)

    def test_get_methylation(self):
        response = self.client.get(f'/api/methylation?case_id={self.case_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue('regions' in data or 'methylation_regions' in data)
        regs = data.get('regions') or data.get('methylation_regions')
        self.assertGreater(len(regs), 0)

    def test_get_locus_svg(self):
        response = self.client.get(f'/api/locus/svg?case_id={self.case_id}&chrom=chr17&start=7670000&end=7680000')
        self.assertEqual(response.status_code, 200)
        self.assertIn('image/svg+xml', response.content_type)
        self.assertIn(b'<svg', response.data)

    def test_snv_aggregate_metrics_beyond_page_limit(self):
        """Test that SNV summary metrics calculate across the entire dataset, not just the page limit."""
        # Query with limit = 10
        response = self.client.get(f'/api/variants/snv?case_id={self.case_id}&limit=10')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['variants']), 10)
        
        # Metrics must reflect the full filtered dataset, not just 2
        metrics = data.get('metrics', {})
        self.assertIn('total', metrics)
        self.assertIn('pathogenic_count', metrics)
        self.assertIn('vus_count', metrics)
        self.assertIn('phased_count', metrics)
        self.assertGreater(metrics['total'], 2)
        self.assertEqual(metrics['total'], data['total_records'])

    def test_gene_panels_crud_and_versioning(self):
        """Test Gene Panel listing, detail fetching, creation, version bumping, and filtering."""
        # 1. List default seeded panels
        res = self.client.get('/api/panels')
        self.assertEqual(res.status_code, 200)
        p_data = json.loads(res.data)
        self.assertGreaterEqual(p_data.get('count', 0), 6)
        
        # 2. Get panel detail
        p1_res = self.client.get('/api/panels/1')
        self.assertEqual(p1_res.status_code, 200)
        p1 = json.loads(p1_res.data).get('panel', {})
        self.assertEqual(p1.get('code'), 'ACMG_SF_V3_2')
        self.assertGreaterEqual(len(p1.get('active_genes', [])), 80)
        self.assertIn('TP53', p1['active_genes'])

        # 3. Filter SNVs using panel 1
        snv_res = self.client.get(f'/api/variants/snv?case_id={self.case_id}&panel_id=1')
        self.assertEqual(snv_res.status_code, 200)
        snv_data = json.loads(snv_res.data)
        for v in snv_data['variants']:
            self.assertIn(v['gene_symbol'].upper(), p1['active_genes'])

        # 4. Create a new custom panel with unique code
        import uuid
        test_code = f"TEST_NEURO_{uuid.uuid4().hex[:6].upper()}"
        create_res = self.client.post('/api/panels', json={
            'name': 'Test Neuro Panel',
            'code': test_code,
            'category': 'Neurology',
            'version': 'v1.0',
            'description': 'Diagnostic ataxia genes',
            'genes': ['FXN', 'ATXN1', 'ATXN2'],
            'changelog': 'Initial creation',
            'author': 'Tester'
        })
        self.assertEqual(create_res.status_code, 201)
        new_id = json.loads(create_res.data)['panel_id']

        # 5. Bump version to v1.1 with new gene
        bump_res = self.client.post(f'/api/panels/{new_id}/versions', json={
            'version': 'v1.1',
            'genes': ['FXN', 'ATXN1', 'ATXN2', 'CACNA1A'],
            'changelog': 'Added CACNA1A for episodic ataxia',
            'author': 'Tester'
        })
        self.assertEqual(bump_res.status_code, 200)
        bump_data = json.loads(bump_res.data)
        self.assertEqual(bump_data['gene_count'], 4)

        # 6. Verify version history shows 2 versions and v1.1 is active
        det_res = self.client.get(f'/api/panels/{new_id}')
        det_data = json.loads(det_res.data)['panel']
        self.assertEqual(len(det_data['versions']), 2)
        self.assertEqual(det_data['versions'][0]['version_str'], 'v1.1')
        self.assertTrue(det_data['versions'][0]['is_active'])
        self.assertFalse(det_data['versions'][1]['is_active'])
        self.assertIn('CACNA1A', det_data['active_genes'])

    def test_igv_genomes_and_config(self):
        """Test local IGV genome registry and config endpoint."""
        r_gen = self.client.get('/api/igv/genomes.json')
        self.assertEqual(r_gen.status_code, 200)
        genomes = json.loads(r_gen.data)
        self.assertEqual(genomes[0]['id'], 'hg38')

        r_cfg = self.client.get(f'/api/igv/config?case_id={self.case_id}')
        self.assertEqual(r_cfg.status_code, 200)
        cfg = json.loads(r_cfg.data).get('config', {})
        self.assertEqual(cfg.get('genome'), 'hg38')
        # Ensure tracks contain local phased BAM and clean GRCh38 tracks
        track_names = [t['name'] for t in cfg.get('tracks', [])]
        self.assertTrue(any('Phased' in n for n in track_names))
        # Ensure Tier 1 GRCh37 VCF is not in tracks
        self.assertFalse(any('Tier 1' in n for n in track_names))

    def test_gene_search_api(self):
        """Test the gene search and genomic coordinate resolver endpoint."""
        # Exact match
        r1 = self.client.get('/api/genes/search?q=TP53')
        self.assertEqual(r1.status_code, 200)
        d1 = json.loads(r1.data)
        self.assertTrue(d1['count'] > 0)
        self.assertEqual(d1['genes'][0]['symbol'], 'TP53')
        self.assertEqual(d1['genes'][0]['chrom'], 'chr17')

        # Prefix match
        r2 = self.client.get('/api/genes/search?q=BRCA')
        self.assertEqual(r2.status_code, 200)
        d2 = json.loads(r2.data)
        symbols = [g['symbol'] for g in d2['genes']]
        self.assertIn('BRCA1', symbols)
        self.assertIn('BRCA2', symbols)

        # Non-existent / fake gene
        r3 = self.client.get('/api/genes/search?q=MUC444')
        self.assertEqual(r3.status_code, 200)
        d3 = json.loads(r3.data)
        self.assertEqual(d3['count'], 0)
        self.assertEqual(d3['genes'], [])

    def test_methylation_zero_simulation_policy(self):
        """Test strict Zero-Simulation Policy for methylation visualization."""
        # 1. Fake gene must return 404 error rather than generating fabricated data
        r_fake = self.client.get('/api/methylation/methylartist?case_id=1&gene=MUC444')
        self.assertEqual(r_fake.status_code, 404)
        d_fake = json.loads(r_fake.data)
        self.assertEqual(d_fake['status'], 'error')
        self.assertIn('Zero Simulation Policy', d_fake['message'])

        # 2. Invented chromosome (chr166) must return 400 error immediately
        r_chr166 = self.client.get('/api/methylation/methylartist?chrom=chr166&start=1000&end=5000')
        self.assertEqual(r_chr166.status_code, 400)
        d_chr166 = json.loads(r_chr166.data)
        self.assertIn("Contig 'chr166' is invalid", d_chr166['message'])

        # 3. Authentic gene in case 1 (MLH1) must return 200 SVG without fabricated exons
        r_real = self.client.get('/api/methylation/methylartist?case_id=1&gene=MLH1')
        self.assertEqual(r_real.status_code, 200)
        svg_content = r_real.get_data(as_text=True)
        self.assertIn('<svg', svg_content)
        self.assertIn('MLH1', svg_content)
        self.assertNotIn('Exon 1', svg_content)

    def test_igv_refseq_and_bam_config(self):
        """Test IGV config includes real RefSeq track, CMRG track, and high-performance BAM parameters."""
        res = self.client.get(f'/api/igv/config?case_id={self.case_id}')
        self.assertEqual(res.status_code, 200)
        tracks = json.loads(res.data)['config']['tracks']
        track_names = [t['name'] for t in tracks]
        
        self.assertIn('NCBI RefSeq Genes', track_names)
        self.assertIn('CMRG Challenging Medical Genes (Benchmark)', track_names)
        
        bam_track = next(t for t in tracks if t['format'] == 'bam')
        self.assertEqual(bam_track['visibilityWindow'], 30000)
        self.assertEqual(bam_track['samplingDepth'], 30)

if __name__ == '__main__':
    unittest.main()


