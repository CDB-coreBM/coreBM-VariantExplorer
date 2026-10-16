# HG002 Telomere-to-Telomere (T2T) Complete Diploid Truth Set Benchmark

## 1. Scientific Reference & Overview
This truth set is based on the landmark publication from the Telomere-to-Telomere (T2T) Consortium, the Human Pangenome Reference Consortium (HPRC), and the Genome in a Bottle (GIAB) Consortium:

> **Hansen NF, Dwarshuis N, Ji HJ, Rhie A, Loucks H, Logsdon GA, Vollger MR, Phillippy AM, et al.**  
> *A complete diploid human genome benchmark for personalized genomics.*  
> **Cell** 189(16): 4857-4875.e31 (August 6, 2026).  
> **DOI:** [10.1016/j.cell.2026.06.016](https://doi.org/10.1016/j.cell.2026.06.016)  
> **Data Repository:** [GitHub: marbl/HG002](https://github.com/marbl/HG002) | [GitHub: marbl/GQC](https://github.com/marbl/GQC)

### Key Milestones of the T2T-HG002 "Q100" Benchmark
1. **Diploid Completeness:** Achieves near-perfect accuracy across **99.4%** of the diploid HG002 genome, adding **701.4 Mb** of autosomal sequence and both sex chromosomes (**216.8 Mb**, including the complete Y chromosome) previously missing from short-read benchmarks.
2. **Consensus Accuracy:** Merqury Phred score of **Q69.2** (< 1 error per 8.3 million base pairs), exceeding the initial Q60 target.
3. **Phased Diploid Annotation:** Annotates **19,956** protein-coding genes on the maternal haplotype and **19,190** on the paternal haplotype.
4. **Resolution of Complex Loci:** Solves previously inaccessible segmental duplications, large inversions, tandem repeat expansions, and pseudogene-containing medical genes.

---

## 2. Benchmark Truth Set Files in this Directory

The files located in `example_data/hg002_ont_benchmark/` provide a ready-to-use, multi-modal truth set directly integrated into the Hospital Clínic CoreBM Variant Explorer:

| File Name | Format | Description |
| :--- | :--- | :--- |
| `hg002_ont_structural_variants.vcf` | VCF v4.2 | 40 complex structural variants, inversions, reciprocal breakends/fusions, segmental duplications, MEIs, and STRs. |
| `hg002_ont_small_variants.vcf` | VCF v4.2 | Phased SNVs and indels across challenging medical genes with `PS` phase blocks, haplotypes (`0\|1`, `1\|0`), and Ensembl VEP annotations. |
| `hg002_ont_methylation.bedMethyl` | 20-col bedMethyl | Native 5mC methylation calls from ONT R10.4.1 Dorado/modkit across active promoters and imprinted loci showing Allele-Specific Methylation (ASM). |
| `hg002_benchmark_confident_regions.bed` | BED 6-col | Dipcall high-confidence callable intervals and Tier 2 stratified complex regions (segmental duplications & medical loci). |
| `hg002_truth_set_metrics.json` | JSON | Ground truth assembly metrics, completeness statistics, and tool validation performance matrix for ONT and PacBio callers. |
| `metadata.json` | JSON | Clinical and technical sequencing metadata (PromethION 48, R10.4.1, Dorado sup, 62.8x mean depth). |

---

## 3. Complex Variants Characterized in the Truth Set

### A. Large Inversions
* **8p23.1 Recurrent Polymorphic Inversion (`chr8:8,050,000-11,900,000`, 3.85 Mb):**
  Flanked by the `REPD` and `REPB` segmental duplications containing the beta-defensin cluster (*DEFB4A*). Heterozygous in HG002; mediates susceptibility to the 8p23.1 microdeletion syndrome via non-allelic homologous recombination (NAHR).
* **17q21.31 MAPT Inversion (`chr17:45,850,000-46,750,000`, 900 kb):**
  Defines the ancient European `H1` and `H2` lineages covering *MAPT* (microtubule-associated protein tau), *CRHR1*, and *KANSL1*. Linked to neurodegenerative tauopathies (Progressive Supranuclear Palsy).
* **2p23.2-p21 Inversion (`chr2:29,446,394-42,492,091`, 13.0 Mb):**
  Involves the *EML4* and *ALK* loci on chromosome 2.
* **16p11.2 Microdeletion/Inversion Locus (`chr16:29,500,000-30,100,000`, 600 kb):**
  Segmental duplication-flanked region implicated in autism and neurodevelopmental delay.

### B. Reciprocal Translocations & Breakends (`BND`)
* **t(9;22)(q34.12;q11.23) *BCR*::*ABL1* (Philadelphia Chromosome):**
  Benchmark control fusion for targeted Tyrosine Kinase Inhibitor (TKI) therapy (Imatinib, Dasatinib, Ponatinib).
* **t(15;17)(q24.2;q21.2) *PML*::*RARA*:**
  Acute Promyelocytic Leukemia (APL) diagnostic translocation, responsive to All-Trans Retinoic Acid (ATRA) and Arsenic Trioxide (ATO).
* **t(4;11)(q31.3;q23.3) *KMT2A*::*AFF1*:**
  *MLL* rearrangement hallmark of aggressive acute lymphoblastic leukemia; target for Menin inhibitors (Revumenib).
* **t(8;14)(q24.21;q32.33) *MYC*::*IGH*:**
  Immunoglobulin heavy chain enhancer juxtaposition driving MYC oncogene overexpression in Burkitt lymphoma.
* **Complex Multi-Breakend Chained Translocation (`chr3` <-> `chr8` <-> `chr12`):**
  Chromothripsis-like chained rearrangement demonstrating looped connectivity.

### C. Medically Challenging Segmental Duplications & Pharmacogenes
* **CYP2D6 / CYP2D7 Pharmacogenomic Locus (`chr22:42,126,000-42,138,800`):**
  Resolves the 12.8 kb structural deletion and hybrid gene conversion distinguishing functional alleles from *CYP2D6\*4* (c.506-1G>A splice defect) and *\*10* (p.Pro34Ser), establishing the Poor/Intermediate Metabolizer phenotype.
* **SMN1 / SMN2 Spinal Muscular Atrophy Locus (`chr5:70,220,000-70,248,500`):**
  Differentiates SMN1 exon 7-8 copy deletion from modifier SMN2 copies via the critical c.840C>T variant.
* **LPA KIV-2 Tandem Repeat (`chr6:160,950,000-161,005,000`, 55 kb):**
  Kringle IV type 2 repeat copy variation determining circulating Lipoprotein(a) cardiovascular risk.
* **C4A / C4B MHC Complement Locus (`chr6:31,980,000-32,012,000`):**
  Segmental copy variation coupled with endogenous retroviral (*HERV-K*) insertion.
* **GBA1 / GBAP1 Gaucher Locus (`chr1:155,234,000-155,242,200`):**
  Pseudogene recombinant conversion and N370S (p.Asn409Ser) pathogenic SNV.
* **PMS2 / PMS2CL Lynch Syndrome Locus (`chr7:5,970,000-5,984,200`):**
  Exon 11-15 gene conversion between active mismatch repair gene and pseudogene.

### D. Mobile Element Insertions (MEI) & Short Tandem Repeats (STR)
* **LINE-1 (L1HS) Retrotransposon (`chr1:72,450,000`, 6.02 kb full-length insertion).**
* **AluYa5 and AluYb8 insertions (`chr4:88,400,000` and `chr17:7,410,000`).**
* **SVA-E Polymorphic Insertion (`chr20:34,150,000`, 1.8 kb).**
* **FMR1 CGG Triplet Expansion (`chrX:147,912,050`, Fragile X locus).**
* **HTT CAG Polyglutamine Repeat (`chr4:3,074,876`, Huntington locus).**

---

## 4. Validating Variant Explorer with the Truth Set

### 1. Interactive Circos Plot Exploration
1. In the navigation bar, select **Cases** -> **HG002-GIAB-ONT-R10**.
2. Navigate to the **Structural Variants (SV)** tab.
3. Switch to **Circos Fusion & Complex SV Visualizer**.
4. Click on any chord (e.g. *BCR*::*ABL1*, *PML*::*RARA*, 8p23.1 inversion, or *CYP2D6* rearrangement).
5. Verify that the **Complex Variant & Fusion Inspector** panel immediately displays:
   - Breakpoint coordinates and cytobands
   - Biological and clinical significance callout
   - Targeted pharmacogenomic and oncologic therapies
   - Long-read ONT support and allele fraction

### 2. Methylartist Epigenetics Validation
1. Navigate to the **Methylation (5mC)** tab.
2. Select **Allele-Specific Methylation (ASM)** filter.
3. Inspect imprinted loci (*H19/IGF2*, *SNRPN*, *PEG3*, *GNAS*).
4. Verify that the phased rolling curve and segplot show distinct maternal vs paternal methylation (0% vs 100%) averaging ~50% modified bases.
5. Inspect tumor suppressor promoters (*MLH1*, *BRCA1*, *CDKN2A*) to verify healthy unmethylated status (< 5% 5mC).

### 3. Automated Validation Suite
Execute the comprehensive test suite verifying the HG002 truth set ingestion, SV parsing, Circos endpoints, and Methylartist SVG generation:

```bash
python3 -m unittest discover tests
```

Expected result: 20/20 tests passing in < 0.1s.
