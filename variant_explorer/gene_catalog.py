"""
Clinical Gene Catalog and Genomic Coordinate Resolver for GRCh38 / hg38.
Resolves gene symbols, aliases, and cytobands for Locus Browser and DNA Methylation.
"""

import os
import sqlite3
from typing import Dict, Any, List, Optional

# Canonical GRCh38 coordinates for major clinical, cancer, and ACMG genes
CANONICAL_GENE_COORDINATES: Dict[str, Dict[str, Any]] = {
    "TP53": {"chrom": "chr17", "start": 7668402, "end": 7687538, "strand": "-", "description": "Tumor Protein P53"},
    "BRCA1": {"chrom": "chr17", "start": 43044295, "end": 43125483, "strand": "-", "description": "BRCA1 DNA Repair Associated"},
    "BRCA2": {"chrom": "chr13", "start": 32315474, "end": 32400266, "strand": "+", "description": "BRCA2 DNA Repair Associated"},
    "EGFR": {"chrom": "chr7", "start": 55019017, "end": 55211628, "strand": "+", "description": "Epidermal Growth Factor Receptor"},
    "KRAS": {"chrom": "chr12", "start": 25205246, "end": 25250929, "strand": "-", "description": "KRAS Proto-Oncogene, GTPase"},
    "BRAF": {"chrom": "chr7", "start": 140719327, "end": 140924929, "strand": "-", "description": "B-Raf Proto-Oncogene"},
    "PIK3CA": {"chrom": "chr3", "start": 179148114, "end": 179240093, "strand": "+", "description": "Phosphatidylinositol-4,5-Bisphosphate 3-Kinase Catalytic Subunit Alpha"},
    "PTEN": {"chrom": "chr10", "start": 87862500, "end": 87971930, "strand": "+", "description": "Phosphatase And Tensin Homolog"},
    "MLH1": {"chrom": "chr3", "start": 36993100, "end": 37050846, "strand": "+", "description": "MutL Homolog 1 (Lynch/CRC)"},
    "MSH2": {"chrom": "chr2", "start": 47403067, "end": 47707914, "strand": "+", "description": "MutS Homolog 2 (Lynch/CRC)"},
    "MSH6": {"chrom": "chr2", "start": 47783389, "end": 47807180, "strand": "+", "description": "MutS Homolog 6 (Lynch/CRC)"},
    "PMS2": {"chrom": "chr7", "start": 5970959, "end": 6009139, "strand": "-", "description": "PMS1 Homolog 2, Mismatch Repair System Component"},
    "MGMT": {"chrom": "chr10", "start": 129467200, "end": 129774600, "strand": "+", "description": "O-6-Methylguanine-DNA Methyltransferase"},
    "CDKN2A": {"chrom": "chr9", "start": 21967751, "end": 21995301, "strand": "+", "description": "Cyclin Dependent Kinase Inhibitor 2A (p16INK4a)"},
    "RB1": {"chrom": "chr13", "start": 48303500, "end": 48481829, "strand": "+", "description": "RB Transcriptional Corepressor 1"},
    "CYP2D6": {"chrom": "chr22", "start": 42125000, "end": 42145000, "strand": "-", "description": "Cytochrome P450 Family 2 Subfamily D Member 6"},
    "GBA1": {"chrom": "chr1", "start": 155233500, "end": 155244500, "strand": "+", "description": "Glucosylceramidase Beta 1 (Gaucher)"},
    "PKD1": {"chrom": "chr16", "start": 2138000, "end": 2185000, "strand": "+", "description": "Polycystin 1, Transient Receptor Potential Channel Interacting (ADPKD)"},
    "HBA1": {"chrom": "chr16", "start": 176680, "end": 177522, "strand": "+", "description": "Hemoglobin Subunit Alpha 1"},
    "HBA2": {"chrom": "chr16", "start": 172876, "end": 173710, "strand": "+", "description": "Hemoglobin Subunit Alpha 2"},
    "HBB": {"chrom": "chr11", "start": 5225464, "end": 5227071, "strand": "-", "description": "Hemoglobin Subunit Beta"},
    "CFTR": {"chrom": "chr7", "start": 117465784, "end": 117670678, "strand": "+", "description": "CF Transmembrane Conductance Regulator (Cystic Fibrosis)"},
    "H19": {"chrom": "chr11", "start": 1977700, "end": 1982700, "strand": "-", "description": "H19 Imprinted Maternally Expressed Transcript (ICR1)"},
    "SNRPN": {"chrom": "chr15", "start": 24955000, "end": 24960000, "strand": "+", "description": "Small Nuclear Ribonucleoprotein Polypeptide N (PWS/AS ICR)"},
    "PEG3": {"chrom": "chr19", "start": 56845000, "end": 56850000, "strand": "+", "description": "Paternally Expressed 3 (Imprinting ICR)"},
    "GNAS": {"chrom": "chr20", "start": 58850000, "end": 58855000, "strand": "+", "description": "GNAS Complex Locus (ASM Imprinting)"},
    "KCNQ1OT1": {"chrom": "chr11", "start": 2720000, "end": 2720800, "strand": "-", "description": "KCNQ1 Opposite Strand/Antisense Transcript 1 (KvDMR1)"},
    "MEG3": {"chrom": "chr14", "start": 100826000, "end": 100826600, "strand": "+", "description": "Maternally Expressed 3 (IG-DMR Imprinting)"},
    "BCR": {"chrom": "chr22", "start": 23180509, "end": 23318037, "strand": "+", "description": "BCR Activator Of RhoGEF And GTPase"},
    "ABL1": {"chrom": "chr9", "start": 130713043, "end": 130887675, "strand": "+", "description": "ABL Proto-Oncogene 1, Non-Receptor Tyrosine Kinase"},
    "DMD": {"chrom": "chrX", "start": 31097677, "end": 33339609, "strand": "-", "description": "Dystrophin (Duchenne / Becker)"},
    "PALB2": {"chrom": "chr16", "start": 23603159, "end": 23641310, "strand": "-", "description": "Partner And Localizer Of BRCA2"},
    "ATM": {"chrom": "chr11", "start": 108222484, "end": 108368590, "strand": "+", "description": "ATM Serine/Threonine Kinase"},
    "CHEK2": {"chrom": "chr22", "start": 28687743, "end": 28742423, "strand": "+", "description": "Checkpoint Kinase 2"},
    "SMAD4": {"chrom": "chr18", "start": 51030206, "end": 51085040, "strand": "+", "description": "SMAD Family Member 4"},
    "APC": {"chrom": "chr5", "start": 112707498, "end": 112846239, "strand": "+", "description": "APC Regulator Of WNT Signaling Pathway"},
    "RET": {"chrom": "chr10", "start": 43572517, "end": 43625799, "strand": "+", "description": "Ret Proto-Oncogene"},
    "MET": {"chrom": "chr7", "start": 116672196, "end": 116798485, "strand": "+", "description": "MET Proto-Oncogene, Receptor Tyrosine Kinase"},
    "ERBB2": {"chrom": "chr17", "start": 39687914, "end": 39730406, "strand": "+", "description": "Erb-B2 Receptor Tyrosine Kinase 2 (HER2)"},
    "ALK": {"chrom": "chr2", "start": 29192774, "end": 29921586, "strand": "-", "description": "ALK Receptor Tyrosine Kinase"},
    "ROS1": {"chrom": "chr6", "start": 117288301, "end": 117425866, "strand": "-", "description": "ROS Proto-Oncogene 1, Receptor Tyrosine Kinase"},
    "FLT3": {"chrom": "chr13", "start": 28013824, "end": 28111226, "strand": "+", "description": "Fms Related Receptor Tyrosine Kinase 3"},
    "NPM1": {"chrom": "chr5", "start": 171387063, "end": 171410719, "strand": "+", "description": "Nucleophosmin 1"},
    "IDH1": {"chrom": "chr2", "start": 208236227, "end": 208266074, "strand": "-", "description": "Isocitrate Dehydrogenase (NADP(+)) 1"},
    "IDH2": {"chrom": "chr15", "start": 90082772, "end": 90103251, "strand": "+", "description": "Isocitrate Dehydrogenase (NADP(+)) 2"},
    "MYC": {"chrom": "chr8", "start": 127735434, "end": 127742951, "strand": "+", "description": "MYC Proto-Oncogene, bHLH Transcription Factor"},
    "KMT2A": {"chrom": "chr11", "start": 118436494, "end": 118526832, "strand": "+", "description": "Lysine Methyltransferase 2A (MLL)"},
    "VHL": {"chrom": "chr3", "start": 10141674, "end": 10153670, "strand": "+", "description": "Von Hippel-Lindau Tumor Suppressor"},
    "WT1": {"chrom": "chr11", "start": 32387775, "end": 32435564, "strand": "-", "description": "WT1 Transcription Factor"},
    "MEN1": {"chrom": "chr11", "start": 64803403, "end": 64812602, "strand": "+", "description": "Menin 1"},
    "NF1": {"chrom": "chr17", "start": 31094927, "end": 31377677, "strand": "+", "description": "Neurofibromin 1"},
    "NF2": {"chrom": "chr22", "start": 29603556, "end": 29698600, "strand": "+", "description": "NF2, Moesin-Ezrin-Radixin-Like Protein"},
    "TSC1": {"chrom": "chr9", "start": 132891349, "end": 132945334, "strand": "-", "description": "TSC Complex Subunit 1"},
    "TSC2": {"chrom": "chr16", "start": 2047985, "end": 2091486, "strand": "-", "description": "TSC Complex Subunit 2"},
    "TTN": {"chrom": "chr2", "start": 178525989, "end": 178830802, "strand": "-", "description": "Titin (Cardiomyopathy)"},
    "MYH7": {"chrom": "chr14", "start": 23412740, "end": 23435682, "strand": "-", "description": "Myosin Heavy Chain 7 (Cardiomyopathy)"},
    "MYBPC3": {"chrom": "chr11", "start": 47332766, "end": 47354110, "strand": "+", "description": "Myosin Binding Protein C3 (Cardiomyopathy)"},
    "TNNT2": {"chrom": "chr1", "start": 201358988, "end": 201377673, "strand": "-", "description": "Troponin T2, Cardiac Type"},
    "TNNI3": {"chrom": "chr19", "start": 55151740, "end": 55157771, "strand": "+", "description": "Troponin I3, Cardiac Type"},
    "LMNA": {"chrom": "chr1", "start": 156082573, "end": 156140089, "strand": "+", "description": "Lamin A/C"},
    "KCNQ1": {"chrom": "chr11", "start": 2441940, "end": 2846187, "strand": "-", "description": "Potassium Voltage-Gated Channel Subfamily Q Member 1 (Long QT)"},
    "KCNH2": {"chrom": "chr7", "start": 150944714, "end": 150978005, "strand": "-", "description": "Potassium Voltage-Gated Channel Subfamily H Member 2 (Long QT)"},
    "SCN5A": {"chrom": "chr3", "start": 38548062, "end": 38649688, "strand": "+", "description": "Sodium Voltage-Gated Channel Alpha Subunit 5 (Brugada / Long QT)"},
    "LDLR": {"chrom": "chr19", "start": 11089363, "end": 11133820, "strand": "+", "description": "Low Density Lipoprotein Receptor (Familial Hypercholesterolemia)"},
    "APOB": {"chrom": "chr2", "start": 21001429, "end": 21044073, "strand": "+", "description": "Apolipoprotein B"},
    "PCSK9": {"chrom": "chr1", "start": 55039447, "end": 55064852, "strand": "+", "description": "Proprotein Convertase Subtilisin/Kexin Type 9"},
    "HFE": {"chrom": "chr6", "start": 26087509, "end": 26095475, "strand": "+", "description": "Homeostatic Iron Regulator (Hemochromatosis)"},
    "GAA": {"chrom": "chr17", "start": 80101563, "end": 80119881, "strand": "-", "description": "Glucosidase Alpha, Acid (Pompe Disease)"},
    "GLA": {"chrom": "chrX", "start": 101397835, "end": 101407886, "strand": "-", "description": "Galactosidase Alpha (Fabry Disease)"},
    "ATP7B": {"chrom": "chr13", "start": 51932616, "end": 52021111, "strand": "+", "description": "ATPase Copper Transporting Beta (Wilson Disease)"},
    "BTD": {"chrom": "chr3", "start": 15685223, "end": 15729111, "strand": "+", "description": "Biotinidase"},
    "FBN1": {"chrom": "chr15", "start": 48408313, "end": 48645709, "strand": "-", "description": "Fibrillin 1 (Marfan Syndrome)"},
    "COL3A1": {"chrom": "chr2", "start": 188974390, "end": 189012749, "strand": "-", "description": "Collagen Type III Alpha 1 Chain (Vascular Ehlers-Danlos)"},
}

class GeneCatalog:
    """Singleton catalog indexing genes from canonical lists, CMRG benchmark BED, and database variants."""
    _instance = None
    _catalog: Dict[str, Dict[str, Any]] = {}
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GeneCatalog, cls).__new__(cls)
            cls._instance._load_catalog()
        return cls._instance

    def _load_catalog(self):
        if self._initialized:
            return

        # 1. Seed with canonical coordinates
        for symbol, entry in CANONICAL_GENE_COORDINATES.items():
            self._catalog[symbol.upper()] = {
                "symbol": symbol.upper(),
                "chrom": entry["chrom"],
                "start": entry["start"],
                "end": entry["end"],
                "strand": entry.get("strand", "+"),
                "description": entry.get("description", ""),
                "source": "Canonical RefSeq / ACMG"
            }

        # 2. Ingest CMRG benchmark BED
        bed_path = os.path.join(
            os.path.dirname(__file__), "..", "data_store", "samples", "HG002", "GRCh38_CMRG_benchmark_gene_coordinates.bed"
        )
        if os.path.exists(bed_path):
            try:
                with open(bed_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        parts = line.split("\t")
                        if len(parts) >= 4:
                            chrom, start_str, end_str, symbol = parts[0], parts[1], parts[2], parts[3].strip().upper()
                            try:
                                s, e = int(start_str), int(end_str)
                                if symbol not in self._catalog:
                                    self._catalog[symbol] = {
                                        "symbol": symbol,
                                        "chrom": chrom,
                                        "start": s,
                                        "end": e,
                                        "strand": "+",
                                        "description": "Challenging Medical Gene (CMRG v1.00)",
                                        "source": "GIAB CMRG Benchmark"
                                    }
                            except ValueError:
                                pass
            except Exception as e:
                print(f"Notice: CMRG BED ingest exception: {e}")

        # 3. Pull from SQLite database if exists
        db_path = os.path.join(os.path.dirname(__file__), "..", "variant_explorer.db")
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                # From methylation_regions
                c.execute("SELECT gene_symbol, chrom, start, end, clinical_significance FROM methylation_regions WHERE gene_symbol IS NOT NULL")
                for r in c.fetchall():
                    sym = r[0].strip().upper()
                    if sym and sym not in self._catalog:
                        self._catalog[sym] = {
                            "symbol": sym,
                            "chrom": r[1],
                            "start": r[2],
                            "end": r[3],
                            "strand": "+",
                            "description": r[4] or "Clinical Epigenetic Target",
                            "source": "Diagnostic Methylation Catalog"
                        }

                # From variants_snv
                c.execute("""
                    SELECT gene_symbol, chrom, MIN(pos), MAX(pos) 
                    FROM variants_snv 
                    WHERE gene_symbol IS NOT NULL AND gene_symbol != '' 
                    GROUP BY gene_symbol, chrom
                """)
                for r in c.fetchall():
                    sym = r[0].strip().upper()
                    if sym and sym not in self._catalog:
                        pad = 5000
                        self._catalog[sym] = {
                            "symbol": sym,
                            "chrom": r[1],
                            "start": max(1, r[2] - pad),
                            "end": r[3] + pad,
                            "strand": "+",
                            "description": "Patient Sequenced Variant Gene",
                            "source": "ONT Patient VCF"
                        }
                conn.close()
            except Exception as e:
                print(f"Notice: SQLite gene catalog query exception: {e}")

        self._initialized = True

    def search(self, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Searches gene catalog by symbol prefix or substring."""
        if not query:
            # Return top clinical genes
            top_symbols = ["TP53", "BRCA1", "BRCA2", "EGFR", "MLH1", "MSH2", "MGMT", "CYP2D6", "PKD1", "CFTR"]
            return [self._catalog[s] for s in top_symbols if s in self._catalog]

        q = query.strip().upper()
        exact_matches = []
        prefix_matches = []
        substring_matches = []

        for symbol, data in self._catalog.items():
            if symbol == q:
                exact_matches.append(data)
            elif symbol.startswith(q):
                prefix_matches.append(data)
            elif q in symbol:
                substring_matches.append(data)

        # Sort prefix and substring matches alphabetically
        prefix_matches.sort(key=lambda x: x["symbol"])
        substring_matches.sort(key=lambda x: x["symbol"])

        combined = exact_matches + prefix_matches + substring_matches
        return combined[:limit]

    def get_gene(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Exact lookup for a gene symbol."""
        if not symbol:
            return None
        return self._catalog.get(symbol.strip().upper())

# Global helper functions
def search_genes(query: str, limit: int = 15) -> List[Dict[str, Any]]:
    return GeneCatalog().search(query, limit)

def get_gene_coordinates(symbol: str) -> Optional[Dict[str, Any]]:
    return GeneCatalog().get_gene(symbol)
