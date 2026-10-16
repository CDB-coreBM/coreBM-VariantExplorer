# 🧬 coreBM Variant Explorer: Long-Read (ONT) Clinical Variant Interpretation Suite

A modern, high-throughput clinical variant interpretation portal tailored for **Oxford Nanopore Technologies (ONT)** long-read sequencing data, incorporating **Hospital Clínic Barcelona** clinical aesthetics.

## Key Capabilities (v1.2.0)
- **Small Variants (SNVs & Indels)**: Native support for Clair3 and DeepVariant calls, including homopolymer error handling, read phasing (`PS`), automated ACMG/AMP 5-tier classification, and AMP/ASCO/CAP somatic tiering.
- **Structural Variants (Table First & Interactive Circos)**: Default starting point is the tabular callset for high-density filtering of breakpoints, length, depth, and TR annotations, with one-click access to the **Interactive Circos Fusion Studio** for complex structural rearrangements (*BCR*::*ABL1*, *KMT2A*::*AFF1*, *EML4*::*ALK*).
- **DNA Methylation & Epigenetics (Table First & Methylartist Studio)**: Ingests modkit 18-column `bedMethyl` and DMR tables with filterable metrics (Mean 5mC %, CpG counts, imprinting). Features an interactive switcher to the **Methylartist Epigenetic Studio** rendering Aggregate 5mC, Phased Haplotypes (HP1 vs HP2), Single-Read 5mC Segplots, and CpG island densities.
- **Tandem Repeat Expansions (TRGT / Straglr)**: Dedicated clinical section for short tandem repeat expansions (*HTT*, *C9orf72*, *FMR1*, *FXN*, *DMPK*, *ATXN1*, *ATXN2*, *ATXN3*, *CACNA1A*, *ATXN7*) with haplotype-resolved repeat copy sizing, disease cutoffs, and direct IGV locus inspection.
- **Clinical Gene Panel Management & HGNC Validation**: Create, version, and curate custom clinical panels with live HGNC gene validation and fuzzy match typo corrections (e.g. `BRAFF` &rarr; `BRAF`).
- **Persistent Clinical Reporting**: Findings added to reports are stored permanently in the SQLite database per case with full clinician audit trails, supporting inline curation note editing and surviving server reboots.
- **Broad IGV.js Multi-Track Genomic Browser**: Local streaming IGV.js instance with nucleotide-level resolution, phased reads (HP1/HP2), CMRG medical genes, and SV breakpoint junctions.
- **GIAB HG002 Platinum Benchmark**: Bundled with Oxford Nanopore PromethION R10.4.1 benchmark data for HG002 (NA24385).

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server (default port: 5050)
python3 run_server.py
```
Visit `http://localhost:5050` in your web browser.
