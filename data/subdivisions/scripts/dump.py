from data.utils import *
from data.subdivisions.utils import SubdivisionMap

SUBDIVISIONS_DATA_PATH = DATA_PATH / "subdivisions"


def dump(sub_map: SubdivisionMap):
    subdivisions = sub_map.all()

    dump_data(subdivisions, SUBDIVISIONS_DATA_PATH / "subdivisions.json.gz")
    dump_lookup_index(
        subdivisions, SUBDIVISIONS_DATA_PATH / "subdivisions_lookup_index.json.gz"
    )
    dump_filter_index(
        subdivisions, SUBDIVISIONS_DATA_PATH / "subdivisions_filter_index.json.gz"
    )
    dump_search_index(
        subdivisions, SUBDIVISIONS_DATA_PATH / "subdivisions_search_index.json.gz"
    )
