"""Curated clinical catalogs, ACMG guidelines, and oncogenic driver annotations."""

from typing import Dict, Any, Optional, Set

# ACMG SF v3.2 Secondary Findings 73 Genes List (Miller et al. 2023)
ACMG_73_GENES: Set[str] = {
    "ACTA2", "ACTC1", "APC", "APOB", "ATP7B", "BAG3", "BMPR1A", "BRCA1", "BRCA2",
    "BTD", "CACNA1S", "CALM1", "CALM2", "CALM3", "CASQ2", "COL3A1", "DES", "DSC2",
    "DSG2", "DSP", "FBN1", "FLNC", "GAA", "GLA", "HFE", "HNF1A", "KCNH2", "KCNQ1",
    "LDLR", "LMNA", "MAX", "MEN1", "MLH1", "MSH2", "MSH6", "MUTYH", "MYBPC3", "MYH11",
    "MYH7", "MYL2", "MYL3", "NF2", "OTC", "PALB2", "PCSK9", "PKP2", "PMS2", "PRKAG2",
    "PTEN", "RB1", "RBM20", "RET", "RIT1", "RYR1", "RYR2", "SCN5A", "SDHAF2", "SDHB",
    "SDHC", "SDHD", "SMAD3", "SMAD4", "STK11", "TGFBR1", "TGFBR2", "TMEM43", "TNNI3",
    "TNNT2", "TP53", "TPM1", "TRDN", "TSC1", "TSC2", "TTN", "VHL", "WT1"
}

# Major Cancer Drivers & Actionable Biomarkers (OncoKB / COSMIC / CAP / AMP)
CANCER_DRIVER_GENES: Dict[str, Dict[str, Any]] = {
    "TP53": {"role": "Tumor Suppressor", "pathways": ["Cell Cycle", "DNA Repair"], "actionable": True},
    "BRCA1": {"role": "Tumor Suppressor", "pathways": ["Homologous Recombination", "PARPi Target"], "actionable": True},
    "BRCA2": {"role": "Tumor Suppressor", "pathways": ["Homologous Recombination", "PARPi Target"], "actionable": True},
    "EGFR": {"role": "Oncogene", "pathways": ["RTK/RAS/MAPK", "EGFR TKI Target"], "actionable": True},
    "KRAS": {"role": "Oncogene", "pathways": ["RTK/RAS/MAPK", "KRAS G12C Inhibitors"], "actionable": True},
    "BRAF": {"role": "Oncogene", "pathways": ["MAPK Pathway", "BRAF/MEK Inhibitors"], "actionable": True},
    "PIK3CA": {"role": "Oncogene", "pathways": ["PI3K/AKT/mTOR", "PI3K Inhibitor Target"], "actionable": True},
    "PTEN": {"role": "Tumor Suppressor", "pathways": ["PI3K/AKT/mTOR"], "actionable": True},
    "MLH1": {"role": "Mismatch Repair", "pathways": ["MMR-D / MSI-H", "Immunotherapy (ICI)"], "actionable": True},
    "MSH2": {"role": "Mismatch Repair", "pathways": ["MMR-D / MSI-H", "Immunotherapy (ICI)"], "actionable": True},
    "MSH6": {"role": "Mismatch Repair", "pathways": ["MMR-D / MSI-H", "Immunotherapy (ICI)"], "actionable": True},
    "PMS2": {"role": "Mismatch Repair", "pathways": ["MMR-D / MSI-H", "Immunotherapy (ICI)"], "actionable": True},
    "ERBB2": {"role": "Oncogene", "pathways": ["HER2 / Trastuzumab Target"], "actionable": True},
    "MET": {"role": "Oncogene", "pathways": ["MET Exon 14 / Amp", "MET Inhibitors"], "actionable": True},
    "ALK": {"role": "Oncogene", "pathways": ["Fusion Driver", "ALK TKIs"], "actionable": True},
    "ROS1": {"role": "Oncogene", "pathways": ["Fusion Driver", "ROS1 TKIs"], "actionable": True},
    "RET": {"role": "Oncogene", "pathways": ["Fusion/Mutation", "RET Inhibitors"], "actionable": True},
    "NTRK1": {"role": "Oncogene", "pathways": ["TRK Fusions", "Larotrectinib/Entrectinib"], "actionable": True},
    "NTRK2": {"role": "Oncogene", "pathways": ["TRK Fusions"], "actionable": True},
    "NTRK3": {"role": "Oncogene", "pathways": ["TRK Fusions"], "actionable": True},
    "IDH1": {"role": "Oncogene", "pathways": ["Metabolism / Epigenetics", "IDH Inhibitors"], "actionable": True},
    "IDH2": {"role": "Oncogene", "pathways": ["Metabolism / Epigenetics", "IDH Inhibitors"], "actionable": True},
    "MGMT": {"role": "DNA Repair", "pathways": ["Alkylating Agent Sensitivity", "Temozolomide"], "actionable": True},
    "DMD": {"role": "Structural/Neuromuscular", "pathways": ["Duchenne/Becker Dystrophy"], "actionable": False},
    "BCR": {"role": "Fusion Partner", "pathways": ["Tyrosine Kinase Fusion", "BCR-ABL1 TKI"], "actionable": True},
    "ABL1": {"role": "Oncogene / Kinase", "pathways": ["Tyrosine Kinase Fusion", "Imatinib/Dasatinib"], "actionable": True},
    "KMT2A": {"role": "Epigenetic Regulator", "pathways": ["MLL Rearrangement", "Menin Inhibitors"], "actionable": True},
    "AFF1": {"role": "Fusion Partner", "pathways": ["KMT2A-AFF1 Translocation", "Leukemia"], "actionable": True},
    "EML4": {"role": "Fusion Partner", "pathways": ["EML4-ALK Inversion", "ALK TKIs"], "actionable": True},
    "MYC": {"role": "Transcription Factor", "pathways": ["MYC-IGH Translocation", "Burkitt / Lymphoma"], "actionable": True},
    "IGH": {"role": "Immunoglobulin Heavy", "pathways": ["Translocation Partner", "Lymphoma"], "actionable": True},
    "FLT3": {"role": "Receptor Tyrosine Kinase", "pathways": ["FLT3-ITD / DUP", "Midostaurin/Gilteritinib"], "actionable": True},
    "NOTCH2": {"role": "Signaling Receptor", "pathways": ["Notch Pathway", "Marginal Zone Lymphoma"], "actionable": True},
}

# Clinically Significant Promoter Methylation & Epigenetic Markers
CLINICAL_METHYLATION_TARGETS: Dict[str, Dict[str, Any]] = {
    "MLH1": {
        "region_type": "Promoter CpG Island",
        "chrom": "chr3",
        "start": 36993100,
        "end": 36993600,
        "significance": "Hypermethylation (>20%) silences MLH1, causing sporadic microsatellite instability (dMMR/MSI-H) and predicts immune checkpoint inhibitor response while ruling out Lynch syndrome in IHC-loss cases.",
        "threshold_hyper": 20.0,
        "threshold_normal": 10.0
    },
    "MGMT": {
        "region_type": "Promoter CpG Island",
        "chrom": "chr10",
        "start": 129467200,
        "end": 129467500,
        "significance": "Promoter hypermethylation (>15%) silences MGMT in glioblastoma / gliomas, predicting favorable response and survival benefit from temozolomide (alkylating chemotherapy).",
        "threshold_hyper": 15.0,
        "threshold_normal": 8.0
    },
    "BRCA1": {
        "region_type": "Promoter CpG Island",
        "chrom": "chr17",
        "start": 43125300,
        "end": 43125600,
        "significance": "Promoter hypermethylation causes epigenetic HRD ('BRCAness') in high-grade serous ovarian cancer and triple-negative breast cancer, conferring PARP inhibitor sensitivity.",
        "threshold_hyper": 25.0,
        "threshold_normal": 5.0
    },
    "CDKN2A": {
        "region_type": "Promoter CpG Island",
        "chrom": "chr9",
        "start": 21994100,
        "end": 21994500,
        "significance": "Hypermethylation silences p16INK4a / p14ARF in melanoma, bladder, and lung cancer.",
        "threshold_hyper": 20.0,
        "threshold_normal": 5.0
    },
    "H19/IGF2": {
        "region_type": "Imprinting Center (ICR1)",
        "chrom": "chr11",
        "start": 1977700,
        "end": 1982700,
        "significance": "Allele-Specific Methylation (ASM): Maternal unmethylated (~50% normal). Loss of imprinting / hypermethylation causes Beckwith-Wiedemann Syndrome (BWS); hypomethylation causes Silver-Russell Syndrome (SRS).",
        "is_imprinted": True,
        "threshold_hyper": 75.0,
        "threshold_hypo": 25.0
    },
    "SNRPN": {
        "region_type": "Imprinting Center (PWS/AS-ICR)",
        "chrom": "chr15",
        "start": 24955000,
        "end": 24960000,
        "significance": "Allele-Specific Methylation (ASM): Maternal methylated, Paternal unmethylated (~50% normal). Hypermethylation (100%) confirms Prader-Willi Syndrome (PWS); hypomethylation (0%) confirms Angelman Syndrome (AS).",
        "is_imprinted": True,
        "threshold_hyper": 85.0,
        "threshold_hypo": 15.0
    },
    "PEG3": {
        "region_type": "Imprinting Center (PEG3-ICR)",
        "chrom": "chr19",
        "start": 56845000,
        "end": 56850000,
        "significance": "Allele-Specific Methylation (ASM): Paternally expressed, maternal allele methylated (~50% normal imprinting control).",
        "is_imprinted": True,
        "threshold_hyper": 80.0,
        "threshold_hypo": 20.0
    },
    "GNAS": {
        "region_type": "Imprinting Center (GNAS-Exon1A)",
        "chrom": "chr20",
        "start": 58850000,
        "end": 58855000,
        "significance": "Allele-Specific Methylation (ASM): Complex imprinting cluster. Loss of imprinting / methylation alteration associated with pseudohypoparathyroidism.",
        "is_imprinted": True,
        "threshold_hyper": 80.0,
        "threshold_hypo": 20.0
    },
    "KCNQ1OT1": {
        "region_type": "Imprinting Center (KvDMR1 / ICR2)",
        "chrom": "chr11",
        "start": 2720000,
        "end": 2720800,
        "significance": "Allele-Specific Methylation (ASM): Maternal methylated (~50% normal). Hypomethylation confirms Beckwith-Wiedemann Syndrome (BWS); hypermethylation in Silver-Russell Syndrome.",
        "is_imprinted": True,
        "threshold_hyper": 80.0,
        "threshold_hypo": 20.0
    },
    "MEG3": {
        "region_type": "Imprinting Center (IG-DMR / 14q32.2)",
        "chrom": "chr14",
        "start": 100826000,
        "end": 100826600,
        "significance": "Allele-Specific Methylation (ASM): Paternal methylated, maternal unmethylated (~50% normal). Hypomethylation confirms Temple syndrome; hypermethylation confirms Kagami-Ogata syndrome.",
        "is_imprinted": True,
        "threshold_hyper": 80.0,
        "threshold_hypo": 20.0
    },
    "TP53": {
        "region_type": "Promoter CpG Island",
        "chrom": "chr17",
        "start": 7676000,
        "end": 7676600,
        "significance": "Tumor suppressor TP53 promoter. Unmethylated (<10%) in normal tissues; rare hypermethylation reported in tumor subtypes.",
        "threshold_hyper": 25.0,
        "threshold_normal": 10.0
    },
    "EGFR": {
        "region_type": "Promoter CpG Island",
        "chrom": "chr7",
        "start": 55086500,
        "end": 55087200,
        "significance": "EGFR oncogene promoter. Hypomethylation maintains open chromatin for RTK signaling.",
        "threshold_hyper": 30.0,
        "threshold_normal": 10.0
    },
    "GBA1": {
        "region_type": "Promoter CpG Island",
        "chrom": "chr1",
        "start": 155233500,
        "end": 155234200,
        "significance": "GBA1 lysosomal enzyme promoter. Unmethylated in normal cells.",
        "threshold_hyper": 25.0,
        "threshold_normal": 10.0
    },
    "CYP2D6": {
        "region_type": "Promoter CpG Island",
        "chrom": "chr22",
        "start": 42125000,
        "end": 42125800,
        "significance": "Pharmacogenomic CYP2D6 locus promoter regulation.",
        "threshold_hyper": 25.0,
        "threshold_normal": 10.0
    },
    "RB1": {
        "region_type": "Promoter CpG Island",
        "chrom": "chr13",
        "start": 48303500,
        "end": 48304200,
        "significance": "Retinoblastoma RB1 promoter. Hypermethylation silences RB1 in retinoblastoma and other cancers.",
        "threshold_hyper": 25.0,
        "threshold_normal": 10.0
    },
    "PTEN": {
        "region_type": "Promoter CpG Island",
        "chrom": "chr10",
        "start": 87862500,
        "end": 87863200,
        "significance": "PTEN tumor suppressor promoter. Epigenetic silencing reduces phosphatase activity in PI3K pathway.",
        "threshold_hyper": 25.0,
        "threshold_normal": 10.0
    }
}
