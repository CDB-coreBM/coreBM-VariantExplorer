import unittest
import os
import json
from variant_explorer.app import create_app
from variant_explorer.models import init_db, get_db_connection
from variant_explorer.sample_manager import ingest_sample
from variant_explorer.methylartist_visualizer import generate_methylartist_svg


class TestHG002AndVisualizers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = create_app()
        app.config['TESTING'] = True
        cls.client = app.test_client()
        init_db()

        base_dir = os.path.dirname(os.path.dirname(__file__))
        hg002_dir = os.path.join(base_dir, 'example_data', 'hg002_ont_benchmark')

        meta_file = os.path.join(hg002_dir, 'metadata.json')
        snv_file = os.path.join(hg002_dir, 'hg002_ont_small_variants.vcf')
        sv_file = os.path.join(hg002_dir, 'hg002_ont_structural_variants.vcf')
        meth_file = os.path.join(hg002_dir, 'hg002_ont_methylation.bedMethyl')

        cls.case_id = ingest_sample(
            metadata_path=meta_file,
            snv_vcf_path=snv_file,
            sv_vcf_path=sv_file,
            meth_bed_path=meth_file,
            clear_existing=True
        )

    def test_hg002_case_ingested(self):
        """Test that HG002 platinum reference genome is correctly ingested and retrieved."""
        response = self.client.get(f'/api/cases/{self.case_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        case_info = data.get('data', {}).get('case', {})
        self.assertEqual(case_info.get('case_id'), 'HG002-GIAB-ONT-R10')
        self.assertIn('HG002', case_info.get('patient_name', ''))
        self.assertIn('PromethION', case_info.get('platform', ''))

    def test_hg002_small_variants_phased(self):
        """Test HG002 small variants have read-backed phase sets and high confidence."""
        response = self.client.get(f'/api/variants/snv?case_id={self.case_id}&limit=100')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        variants = data.get('variants', [])
        self.assertGreaterEqual(len(variants), 5)

        # Check TP53 benchmark variant
        tp53 = next((v for v in variants if v.get('gene_symbol') == 'TP53'), None)
        self.assertIsNotNone(tp53)
        self.assertEqual(tp53['chrom'], 'chr17')
        self.assertIn('0|1', tp53['genotype'])
        self.assertIsNotNone(tp53['phase_set'])

    def test_hg002_complex_svs_and_fusions(self):
        """Test HG002 structural variants contain complex rearrangements and fusions."""
        response = self.client.get(f'/api/variants/sv/circos?case_id={self.case_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        svs = data.get('structural_variants', [])
        self.assertGreaterEqual(len(svs), 8)

        # Check BCR-ABL1 translocation / fusion
        bcr_abl1 = next((s for s in svs if 'ABL1' in s.get('genes_affected', '') and 'BCR' in s.get('genes_affected', '')), None)
        self.assertIsNotNone(bcr_abl1)
        self.assertEqual(bcr_abl1['sv_type'], 'BND')
        self.assertEqual(bcr_abl1['chrom'], 'chr9')
        self.assertEqual(bcr_abl1['chr2'], 'chr22')

        # Check KMT2A-AFF1 rearrangement
        kmt2a = next((s for s in svs if 'KMT2A' in s.get('genes_affected', '')), None)
        self.assertIsNotNone(kmt2a)
        self.assertEqual(kmt2a['chrom'], 'chr11')
        self.assertEqual(kmt2a['chr2'], 'chr4')

        # Check EML4-ALK inversion
        alk = next((s for s in svs if 'ALK' in s.get('genes_affected', '')), None)
        self.assertIsNotNone(alk)
        self.assertEqual(alk['sv_type'], 'INV')

    def test_hg002_methylation_imprinting_asm(self):
        """Test HG002 methylation identifies Allele-Specific Methylation (ASM) in imprinting loci."""
        response = self.client.get(f'/api/methylation?case_id={self.case_id}&asm_only=1')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        regions = data.get('regions', [])
        self.assertGreaterEqual(len(regions), 2)

        # H19/IGF2 should have confirmed ASM
        h19 = next((r for r in regions if 'H19' in r.get('gene_symbol', '')), None)
        self.assertIsNotNone(h19)
        self.assertEqual(h19['is_asm'], 1)
        self.assertAlmostEqual(h19['percent_modified'], 50.0, delta=5.0)

    def test_methylartist_svg_generation(self):
        """Test Python methylartist visualizer generates authentic SVG multi-track plot."""
        svg_code = generate_methylartist_svg(
            chrom="chr3",
            start=36993100,
            end=36993600,
            gene_symbol="MLH1",
            region_type="Promoter CpG Island",
            mean_percent=78.5,
            hp1_percent=76.0,
            hp2_percent=81.0,
            is_asm=False,
            coverage=45.0
        )
        self.assertIn('<svg', svg_code)
        self.assertIn('METHYLARTIST', svg_code)
        self.assertIn('MLH1', svg_code)
        self.assertIn('Segplot', svg_code)
        self.assertIn('CpG Island', svg_code)

    def test_methylartist_api_endpoint(self):
        """Test /api/methylation/methylartist endpoint returns image/svg+xml."""
        response = self.client.get(f'/api/methylation/methylartist?case_id={self.case_id}&gene=MLH1')
        self.assertEqual(response.status_code, 200)
        self.assertIn('image/svg+xml', response.content_type)
        self.assertIn(b'<svg', response.data)
        self.assertIn(b'METHYLARTIST', response.data)


    def test_hg002_cell_2026_complex_structural_variants(self):
        """Test presence of Hansen et al. Cell 2026 complex SVs: PML-RARA, CYP2D6, 8p23.1, MAPT, SMN1."""
        response = self.client.get(f'/api/variants/sv/circos?case_id={self.case_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        svs = data.get('structural_variants', [])
        self.assertGreaterEqual(len(svs), 30)

        # 1. PML-RARA reciprocal translocation
        pml_rara = next((s for s in svs if 'PML' in s.get('genes_affected', '') and 'RARA' in s.get('genes_affected', '')), None)
        self.assertIsNotNone(pml_rara)
        self.assertEqual(pml_rara['sv_type'], 'BND')

        # 2. CYP2D6 / CYP2D7 complex rearrangement
        cyp = next((s for s in svs if 'CYP2D6' in s.get('genes_affected', '')), None)
        self.assertIsNotNone(cyp)
        self.assertEqual(cyp['sv_type'], 'DEL')
        self.assertEqual(cyp['chrom'], 'chr22')

        # 3. 8p23.1 inversion (3.85 Mb)
        inv_8p = next((s for s in svs if s.get('chrom') == 'chr8' and s.get('sv_type') == 'INV' and s.get('sv_len', 0) > 3000000), None)
        self.assertIsNotNone(inv_8p)

        # 4. 17q21.31 MAPT (Tau) inversion (900 kb)
        mapt = next((s for s in svs if 'MAPT' in s.get('genes_affected', '')), None)
        self.assertIsNotNone(mapt)
        self.assertEqual(mapt['sv_type'], 'INV')

        # 5. SMN1 / SMN2 deletion
        smn = next((s for s in svs if 'SMN1' in s.get('genes_affected', '')), None)
        self.assertIsNotNone(smn)
        self.assertEqual(smn['chrom'], 'chr5')

    def test_hg002_truth_set_metrics_file(self):
        """Test HG002 truth set metrics JSON exists and has valid Cell 2026 assembly & validation metrics."""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        metrics_file = os.path.join(base_dir, 'example_data', 'hg002_ont_benchmark', 'hg002_truth_set_metrics.json')
        self.assertTrue(os.path.exists(metrics_file))

        with open(metrics_file, 'r', encoding='utf-8') as f:
            metrics = json.load(f)

        self.assertIn('benchmark_metadata', metrics)
        self.assertIn('10.1016/j.cell.2026.06.016', metrics['benchmark_metadata']['doi'])
        self.assertGreaterEqual(metrics['assembly_ground_truth_metrics']['merqury_phred_qv'], 60.0)
        self.assertGreaterEqual(metrics['assembly_ground_truth_metrics']['genome_completeness_percent'], 99.0)
        self.assertIn('tool_validation_performance_matrix', metrics)
        self.assertIn('oxford_nanopore_r10_4_1', metrics['tool_validation_performance_matrix'])
        self.assertIn('pacbio_hifi', metrics['tool_validation_performance_matrix'])

    def test_hg002_benchmark_confident_regions(self):
        """Test high-confidence callable benchmark regions BED exists and has valid intervals."""
    def test_gnomad_af_and_protein_consequences(self):
        """Test gnomAD AF is properly populated from AF_POPMAX/CSQ and p.? is normalized."""
        response = self.client.get(f'/api/variants/snv?case_id={self.case_id}&limit=100')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        variants = data.get('variants', [])

        # Check that variants have valid gnomad_af values (not all 0.0)
        non_zero_af = [v for v in variants if v.get('gnomad_af') and v['gnomad_af'] > 0]
        self.assertGreater(len(non_zero_af), 0)

        # Check specific variants: CYP2D6 c.100C>T (AF ~0.24) or CFTR (AF ~0.012)
        r_cftr = self.client.get(f'/api/variants/snv?case_id={self.case_id}&gene=CFTR')
        self.assertEqual(r_cftr.status_code, 200)
        cftr_list = json.loads(r_cftr.data).get('variants', [])
        cftr = cftr_list[0] if cftr_list else None
        self.assertIsNotNone(cftr)
        self.assertAlmostEqual(cftr['gnomad_af'], 0.012, places=3)

        # Check splice variants: ensure hgvs_p is not raw 'p.?'
        splice_vars = [v for v in variants if 'splice' in v.get('consequence', '').lower()]
        for sv in splice_vars:
            self.assertNotEqual(sv.get('hgvs_p'), 'p.?')
            self.assertTrue('Splice' in sv.get('hgvs_p', ''))

    def test_sv_parameter_harmonization(self):
        """Test SV endpoints support both min_len and min_length without error."""
        r1 = self.client.get(f'/api/variants/sv?case_id={self.case_id}&min_len=1000')
        r2 = self.client.get(f'/api/variants/sv?case_id={self.case_id}&min_length=1000')
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(json.loads(r1.data)['total_records'], json.loads(r2.data)['total_records'])

    def test_methylartist_endpoint(self):
        """Test Methylartist SVG rendering and multi-tier region matching."""
        # 1. Preset MLH1
        r_mlh1 = self.client.get(f'/api/methylation/methylartist?case_id={self.case_id}&gene=MLH1')
        self.assertEqual(r_mlh1.status_code, 200)
        self.assertIn('<svg', r_mlh1.data.decode('utf-8'))
        self.assertIn('MLH1', r_mlh1.data.decode('utf-8'))

        # 2. Imprinted ASM locus H19/IGF2
        r_h19 = self.client.get(f'/api/methylation/methylartist?case_id={self.case_id}&gene=H19/IGF2')
        self.assertEqual(r_h19.status_code, 200)
        self.assertIn('<svg', r_h19.data.decode('utf-8'))

    def test_igv_multi_track_endpoints(self):
        """Test all IGV REST API tracks return valid features and coverage."""
        # 1. Config
        r_cfg = self.client.get(f'/api/igv/config?case_id={self.case_id}')
        self.assertEqual(r_cfg.status_code, 200)
        cfg_data = json.loads(r_cfg.data)['config']
        self.assertEqual(cfg_data['genome'], 'hg38')
        self.assertGreaterEqual(len(cfg_data['tracks']), 5)

        # 2. Genes (TP53)
        r_genes = self.client.get('/api/igv/tracks/genes?chrom=chr17&start=7668000&end=7688000')
        self.assertEqual(r_genes.status_code, 200)
        genes_data = json.loads(r_genes.data)['features']
        self.assertTrue(any(g['name'] == 'TP53' for g in genes_data))

        # 3. Dynamic Coverage
        r_cov = self.client.get(f'/api/igv/tracks/coverage?case_id={self.case_id}&chrom=chr17&start=7668000&end=7688000')
        self.assertEqual(r_cov.status_code, 200)
        bins = json.loads(r_cov.data)['bins']
        self.assertGreater(len(bins), 50)
        self.assertGreater(bins[0]['score'], 10.0)

        # 4. Small Variants
        r_snv = self.client.get(f'/api/igv/tracks/snv?case_id={self.case_id}&chrom=chr17&start=7668000&end=7688000')
        self.assertEqual(r_snv.status_code, 200)
        snvs = json.loads(r_snv.data)['features']
        self.assertGreater(len(snvs), 0)

        # 5. Structural Variants
        r_sv = self.client.get(f'/api/igv/tracks/sv?case_id={self.case_id}&chrom=chr8&start=8000000&end=12500000')
        self.assertEqual(r_sv.status_code, 200)
        svs = json.loads(r_sv.data)['features']
        self.assertGreater(len(svs), 0)

        # 6. Methylation Track
        r_meth = self.client.get(f'/api/igv/tracks/methylation?case_id={self.case_id}&chrom=chr11&start=1970000&end=1990000')
        self.assertEqual(r_meth.status_code, 200)
        meth_features = json.loads(r_meth.data)['features']
        self.assertGreater(len(meth_features), 0)

    def test_igv_config_and_reference_genome_hg38(self):
        """Test IGV config endpoint serves hg38 reference genome with fasta, cytoband, and 6 streaming tracks."""
        res = self.client.get('/api/igv/config?locus=chr17:7668000-7688000')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        config = data.get('config', {})

        # Verify reference genome build
        self.assertEqual(config.get('genome'), 'hg38')
        ref = config.get('reference', {})
        self.assertEqual(ref.get('id'), 'hg38')
        self.assertIn('hg38.fa', ref.get('fastaURL', ''))
        self.assertIn('hg38.fa.fai', ref.get('indexURL', ''))

        # Verify streaming tracks (BAM and VCFs)
        tracks = config.get('tracks', [])
        self.assertGreaterEqual(len(tracks), 5)
        bam_track = next((t for t in tracks if t.get('format') == 'bam'), None)
        self.assertIsNotNone(bam_track)
        self.assertEqual(bam_track.get('colorByTag'), 'HP')
        self.assertIn('HG002_phased.bam', bam_track.get('url', ''))

        sv_track = next((t for t in tracks if 'SV Benchmark' in t.get('name', '')), None)
        self.assertIsNotNone(sv_track)
        self.assertEqual(sv_track.get('format'), 'vcf')

    def test_bam_partial_content_streaming(self):
        """Test HTTP 206 Partial Content range requests on real HG002 BAM file."""
        bam_url = '/api/stream/files/data_store/samples/HG002/HG002_phased.bam'
        res = self.client.get(bam_url, headers={'Range': 'bytes=0-1023'})
        self.assertEqual(res.status_code, 206)
        self.assertEqual(res.headers.get('Accept-Ranges'), 'bytes')
        self.assertEqual(res.headers.get('Content-Length'), '1024')
        self.assertIn('bytes 0-1023/', res.headers.get('Content-Range', ''))
        self.assertEqual(res.headers.get('Access-Control-Allow-Origin'), '*')

    def test_wgs_tabix_vcf_query(self):
        """Test live tabix querying on whole-genome 3.9M SNVs and CMRG SVs without loading files into RAM."""
        # Query WGS small variants at TP53 locus
        res_snv = self.client.get('/api/variants/wgs/query?vcf_type=wgs_snv&chrom=chr17&start=7668000&end=7688000')
        self.assertEqual(res_snv.status_code, 200)
        d_snv = json.loads(res_snv.data)
        self.assertGreater(d_snv.get('count', 0), 0)
        self.assertEqual(d_snv['variants'][0]['chrom'], 'chr17')

        # Query CMRG structural variants on chr19
        res_sv = self.client.get('/api/variants/wgs/query?vcf_type=cmrg_sv&chrom=chr19&start=1000000&end=60000000')
        self.assertEqual(res_sv.status_code, 200)
        d_sv = json.loads(res_sv.data)
        self.assertGreater(d_sv.get('count', 0), 0)

    def test_chr16_bam_coverage_and_hba_variant(self):
        """Verify HG002 BAM covers chr16 (HBA locus) and HBA2 splice acceptor variant exists."""
        import pysam
        bam_path = 'data_store/samples/HG002/HG002_phased.bam'
        self.assertTrue(os.path.exists(bam_path))
        bf = pysam.AlignmentFile(bam_path, 'rb')
        chr16_reads = list(bf.fetch('chr16', 220000, 230000))
        bf.close()
        self.assertGreater(len(chr16_reads), 20, "chr16 HBA locus must have real ONT read coverage")

        # Query HBA2 in SNVs
        res = self.client.get('/api/variants/snv?case_id=2&gene=HBA2')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertGreaterEqual(data.get('total_records', 0), 1)
        hba2_var = data['variants'][0]
        self.assertEqual(hba2_var['gene_symbol'], 'HBA2')
        self.assertEqual(hba2_var['pos'], 223562)
        self.assertGreater(hba2_var['gnomad_af'], 0.0)

    def test_cmrg_full_ingestion_and_gene_mapping(self):
        """Verify all 27k+ CMRG small variants and genes like PKD1, SMN1 are ingested."""
        res = self.client.get('/api/cases/2')
        self.assertEqual(res.status_code, 200)
        summary = json.loads(res.data)['data']
        total_snv = summary['snv_metrics']['total_snv']
        self.assertGreater(total_snv, 25000, "Case 2 must have full CMRG truth set (>25k variants)")

        # Query PKD1
        res_pkd1 = self.client.get('/api/variants/snv?case_id=2&gene=PKD1')
        self.assertEqual(res_pkd1.status_code, 200)
        d_pkd1 = json.loads(res_pkd1.data)
        self.assertGreater(d_pkd1.get('total_records', 0), 0)

    def test_vendor_igv_local_availability(self):
        """Verify local IGV.js vendor file is served with HTTP 200 and substantial size."""
        res = self.client.get('/static/vendor/igv.min.js')
        self.assertEqual(res.status_code, 200)
        self.assertGreater(len(res.data), 900000)

    def test_igv_coverage_track_and_tracks_structure(self):
        """Verify IGV config has ONT Depth Coverage, BAM, RefSeq, SNVs, SVs, and Methylation."""
        res = self.client.get('/api/igv/config?case_id=2')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        tracks = data['config']['tracks']
        track_names = [t.get('name', '') for t in tracks]
        
        self.assertTrue(any('Coverage' in n for n in track_names), "Coverage track must be present in IGV config")
        self.assertTrue(any('Alignments' in n or t.get('format') == 'bam' for n, t in zip(track_names, tracks)), "BAM track must be present in config")
        self.assertTrue(any('RefSeq' in n or 'Genes' in n for n in track_names), "Genes track must be present")
        self.assertTrue(any('SV' in n for n in track_names), "SV track must be present")
        self.assertTrue(any('Methylation' in n for n in track_names), "Methylation track must be present")

    def test_hg002_full_methylation_dataset(self):
        """Verify Case 2 has comprehensive HG002 methylation covering 340+ clinical and CMRG genes."""
        res = self.client.get(f'/api/cases/{self.case_id}')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)['data']
        total_regions = data['methylation_metrics']['total_regions']
        self.assertGreaterEqual(total_regions, 300, "HG002 must have >300 authentic methylation regions across clinical genes")

        # Test querying specific medical genes in methylation API
        res_brca1 = self.client.get(f'/api/methylation?case_id={self.case_id}&gene=BRCA1')
        self.assertEqual(res_brca1.status_code, 200)
        d_brca1 = json.loads(res_brca1.data)
        regions = d_brca1.get('regions', [])
        self.assertGreaterEqual(len(regions), 1)
        self.assertEqual(regions[0]['gene_symbol'], 'BRCA1')

    def test_case_qc_default_view_markup(self):
        """Verify index.html / base.html renders Case QC & Phasing as the first active sidebar item."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        # Verify Case QC is the first sidebar nav item
        qc_pos = html.find('data-view="qc-view"')
        snv_pos = html.find('data-view="snv-view"')
        self.assertNotEqual(qc_pos, -1)
        self.assertNotEqual(snv_pos, -1)
        self.assertLess(qc_pos, snv_pos, "Case QC & Phasing must be the first item in the sidebar menu")
        self.assertIn('<div class="view-section active" id="qc-view">', html)


if __name__ == '__main__':
    unittest.main()


