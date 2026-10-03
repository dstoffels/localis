from ingest.utils import DATA_PATH
from ingest.utils import dump_data, dump_lookup_index
from ingest.shared.models import MacroregionModel
from ingest.utils import ingest_log

MACROREGIONS_DATA_PATH = DATA_PATH / "macroregions"


def dump(macroregions: list[MacroregionModel]) -> None:
    MACROREGIONS_DATA_PATH.mkdir(parents=True, exist_ok=True)
    ingest_log.writeline(f"Dumping {len(macroregions)} macroregions...")
    dump_data(macroregions, MACROREGIONS_DATA_PATH / "macroregions.tsv")

    ingest_log.writeline("Dumping macroregions lookup indexes...")
    dump_lookup_index(macroregions, MACROREGIONS_DATA_PATH)
