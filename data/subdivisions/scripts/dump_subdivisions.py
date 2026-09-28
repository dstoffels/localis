from data.utils.paths import DATA_PATH
from data.utils.index import (
    dump_data,
    dump_lookup_index,
    dump_filter_index,
    dump_search_index,
)
from data.subdivisions.utils.subdivision_map import SubdivisionMap

SUBDIVISIONS_DATA_PATH = DATA_PATH / "subdivisions"


def dump(sub_map: SubdivisionMap):
    subdivisions = sub_map.all()

    # ensure subdivisions are sorted by admin level so level 2 subdivisions are processed after their level 1 parents
    # subdivisions.sort(key=lambda s: s.admin_level)
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
