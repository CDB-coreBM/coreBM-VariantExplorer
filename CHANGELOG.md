# Changelog

All notable changes to the **coreBM Variant Explorer** platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.3.0] - 2026-10-20

### Added
- **Interactive Tandem Repeat Expansion Sizing Distribution Plot**:
  - Implemented single-molecule sizing distribution plot modeled after ExpansionHunter and TRGT clinical reports.
  - Horizontal multi-gene tracks displaying *ATXN3*, *FXN*, *ATN1*, *AR*, *DMPK*, *HTT*, *FMR1*, *ATXN1*, *ATXN2*, *CACNA1A*, *ATXN7*, *C9orf72*, *RFC1*, and *NOTCH2NLC*.
  - Three distinct background shaded clinical range zones per gene track:
    - **Normal Range**: Sky Blue band (`<= normal_cutoff`).
    - **Risk / Premutation Range**: Soft Cream / Light Amber band (`normal_cutoff` to `pathogenic_cutoff`).
    - **Disease / Full Expansion Range**: Soft Peach / Coral band (`>= pathogenic_cutoff`).
  - Calibrated reference population cohort swarm distribution (Normal = blue, Premutation = amber, Full expansion = crimson).
  - Prominent, high-contrast, glowing diamond marker displaying where the active patient sample falls (showing both Long Allele and Short Allele with clinical classification).
  - Sizing unit toggle: Switch dynamically between **Base Pairs (bp)** (matching ExpansionHunter) and **Repeat Copies**.
  - Interactive SVG tooltips with detailed allele sizing, disease association, and quick action buttons ("Inspect in IGV" and "Add to Report").
  - Publication-grade "Experimental status" legend box.
  - View switcher toolbar to toggle between the **Expansion Sizing Distribution Plot** and the **Repeat Callset Table**.
- **External Standard JSON Catalog for Tandem Repeat Loci (Zero Hard-Coding)**:
  - Replaced all hardcoded loci definitions in Python with a standard external JSON catalog (`variant_explorer/data/tandem_repeat_catalog.json`).
  - Supported multi-tier resolution: `REPEAT_CATALOG_PATH` env var, `data_store/tandem_repeat_catalog.json` user workspace override, or bundled catalog.
  - Hot-reloading on catalog file modification via `mtime` checking without server restarts.
  - REST API endpoint `/api/repeats/catalog` (`GET` to fetch definitions, `POST` to programmatically add or update repeat loci).
  - Recessive inheritance support (e.g. *FXN*, *RFC1*) properly differentiating heterozygous carriers from biallelic expansions.

---

## [1.2.0] - 2026-10-16

### Added
- **Persistent Clinical Report Findings in SQLite**:
  - Implemented `case_report_findings` SQLite table with comprehensive metadata tracking: `finding_type`, `variant_id`, `gene_symbol`, coordinates, ACMG classification, somatic tier, and custom clinical curation notes.
  - Findings added by clinical geneticists now reliably persist across browser reloads, page navigation, and server restarts.
  - RESTful API endpoints for findings: `GET`, `POST`, `PUT`, and `DELETE` under `/api/cases/<case_id>/report_findings`.
  - Added real-time inline note editing (`editFindingNotes`) directly from the Clinical Report view.
- **Dedicated Tandem Repeat Expansions (TRGT / Straglr) Section**:
  - Moved Short Tandem Repeats (STR) out of Case QC into an independent first-class navigation section (`#repeats-view`).
  - Added dedicated endpoint `/api/repeats` and database table `tandem_repeats` supporting single-molecule sizing across *HTT*, *C9orf72*, *FMR1*, *FXN*, *DMPK*, *ATXN1*, *ATXN2*, *ATXN3*, *CACNA1A*, and *ATXN7*.
  - Added interactive filtering by gene symbol, disease, and expansion status (Pathogenic, Premutation, Intermediate, Normal Range).
  - Added direct "Inspect in IGV" locus tracking and "Add to Report" actions for repeat expansions.
- **Gene Symbol Validation for Clinical Panels**:
  - Implemented `/api/genes/validate` endpoint using approved HGNC and CMRG gene catalogs.
  - Added fuzzy string matching with `difflib` for automatic typo correction and suggestions (e.g. `BRAFF` &rarr; `BRAF`, `FXNN` &rarr; `FXN`).
  - Interactive validation in gene panel creation modal with live status chips (green for approved, red/amber for unrecognized) and one-click replacement.
  - Gated panel creation to guard against unverified or misspelled gene symbols.
- **DNA Methylation Callset Table & View Switcher**:
  - Restructured DNA Methylation view to default to a high-density, filterable callset table.
  - Implemented view switcher matching the Structural Variants section to toggle between the **Callset Table** and the **Methylartist Epigenetic Studio**.
  - Added row-level "Inspect in Studio", "IGV Locus", and "Add to Report" shortcuts.

### Changed
- **Structural Variants Default View**:
  - Default view mode for Structural Variants is now the **Callset Table** rather than the interactive Circos plot, providing rapid access to breakpoint coordinates, variant sizes, and read depths upon loading.
  - Preserved full toggle capability to open the Circos fusion viewer on demand via `#svViewCircosBtn`.
- **Case QC & Phasing View Streamlining**:
  - Removed duplicate tandem repeat expansion cards and compound heterozygosity tables from Case QC, ensuring Case QC remains strictly focused on run metrics, base accuracy (Q-scores), read length N50, depth distributions, and phase block continuity.
- **Gene Catalog Enrichment**:
  - Added full GRCh38 canonical coordinates for major repeat-expansion and neurological genes (*FXN*, *ATXN1*, *ATXN2*, *ATXN3*, *CACNA1A*, *ATXN7*, *DMPK*, *FMR1*, *HTT*, *C9orf72*).
  - Synchronized dynamically created panels with catalog lookups.

### Fixed
- Fixed finding removal and note update endpoints to support both database auto-increment IDs and string variant identifiers.
- Resolved race conditions in report builder by synchronizing findings from the backend database upon active case selection.
- Eliminated invalid mock chromosome generations in epigenetic plotting routines.

---

## [1.1.0] - 2026-10-15

### Added
- Native integration with Broad IGV.js v2.15 for nucleotide-resolution multi-track genomic visualization.
- Interactive Circos plot for genome-wide structural rearrangements, inversions, and fusions (*BCR*::*ABL1*, *KMT2A*::*AFF1*).
- GIAB HG002 Platinum Genome ONT PromethION R10.4.1 clinical benchmark datasets.
- Fast gene panel filtering supporting ACMG Secondary Findings v3.2, Hereditary Breast/Ovarian Cancer, Lynch Syndrome, and Cardio/Neuro gene sets.

---

## [1.0.0] - 2026-10-14

### Initial Release
- Initial deployment of CoreBM Long-Read Variant Explorer for Hospital Clínic de Barcelona.
- Clair3 and DeepVariant SNV/Indel calling integration.
- Sniffles2 and cuteSV structural variant parsing.
- Dorado + modkit bedMethyl epigenetic methylation pipeline.
- Automated ACMG/AMP 2015 germline classification and AMP/ASCO/CAP somatic tiering.
