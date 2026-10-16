# 🧬 coreBM Variant Explorer: Long-Read (ONT) Clinical Variant Interpretation Suite

A modern, high-throughput clinical variant interpretation portal tailored for **Oxford Nanopore Technologies (ONT)** long-read sequencing data, incorporating **Hospital Clínic Barcelona** clinical aesthetics.

## Key Capabilities
- **Small Variants (SNVs & Indels)**: Native support for Clair3 and DeepVariant calls, including homopolymer error handling, read phasing (`PS`), automated ACMG/AMP 5-tier classification, and AMP/ASCO/CAP somatic tiering.
- **Structural Variants (SVs >=50 bp)**: Supports Sniffles2, cuteSV, and Severus calls (DEL, INS, DUP, INV, BND / translocations) with tandem-repeat overlap flags, read support thresholds, and interactive breakpoint connection arcs.
- **DNA Methylation & Epigenetics (Methylartist Integration)**: Ingests modkit 18-column `bedMethyl` and DMR tables, tracks 5mC percentage, flags promoter hyper/hypo-methylation in cancer genes (*MLH1*, *MGMT*, *BRCA1*), and resolves Allele-Specific Methylation (ASM) for imprinting disorders. Features a native **Methylartist Epigenetic Studio** rendering multi-track composite plots with Aggregate 5mC, Phased Haplotypes (HP1 vs HP2), Single-Read 5mC Segplots, and CpG island densities.
- **Interactive Circos Plot for Complex SVs & Fusions**: Circular whole-genome ideogram with interactive chord ribbons for complex structural variants, inter-chromosomal translocations (*BCR*::*ABL1*, *KMT2A*::*AFF1*, *MYC*::*IGH*), and inversions (*EML4*::*ALK*). Clicking any chord immediately reveals breakpoint coordinates, fusion partners, clinical targeted therapies, and ONT read support.
- **GIAB HG002 Platinum Genome ONT Benchmark**: Includes public Oxford Nanopore PromethION R10.4.1 benchmark data for HG002 (NA24385) with phased small variants (Clair3), benchmark structural variants (Sniffles2), and direct 5mC methylation profiles (modkit).
- **Interactive Multi-Track Locus Viewer**: Built-in SVG genome inspector with cytoband, transcripts, coverage depth, phased reads, SV junctions, and methylation lollipops.
- **Clinical Reporting**: Comprehensive report builder with clinician interpretation sign-off and printable PDF/HTML export.

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server (default port: 5050)
python3 run_server.py
```
Visit `http://localhost:5050` in your web browser.
