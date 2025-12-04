from data.utils import *
from data.subdivisions.utils import SubdivisionMap

SUBDIVISIONS_DATA_PATH = DATA_PATH / "subdivisions"


def dump(sub_map: SubdivisionMap):
    subdivisions = sub_map.all()
    print(f"Dumping {len(subdivisions)} subdivisions...")
    dump_data(subdivisions, SUBDIVISIONS_DATA_PATH / "subdivisions.tsv")

    print("Dumping subdivision lookup indexes...")
    dump_lookup_index(
        subdivisions, SUBDIVISIONS_DATA_PATH / "subdivisions_lookup_index.tsv"
    )

    print("Dumping subdivision filter index...")
    dump_filter_index(
        subdivisions, SUBDIVISIONS_DATA_PATH / "subdivisions_filter_index.tsv"
    )

    print("Dumping subdivision search index...")
    dump_search_index(
        subdivisions, SUBDIVISIONS_DATA_PATH / "subdivisions_search_index.tsv"
    )
