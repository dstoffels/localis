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

    HEADERS = (
        "id",
        "name",
        "aliases",
        "geonames_code",
        "iso_code",
        "type",
        "admin_level",
        "parent_id",
        "country_id",
    )

    # # Dump subdivision data file
    # with open(
    #     DATA_PATH / "subdivisions.tsv",
    #     "w",
    #     encoding="utf-8",
    #     newline="",
    # ) as f:
    #     writer = csv.DictWriter(f, fieldnames=HEADERS, delimiter="\t")
    #     writer.writeheader()
    #     for sub in subdivisions:
    #         writer.writerow(
    #             {
    #                 "id": sub.id,
    #                 "name": sub.name,
    #                 "aliases": "|".join(sub.aliases),
    #                 "geonames_code": sub.geonames_code,
    #                 "iso_code": sub.iso_code,
    #                 "type": sub.type,
    #                 "admin_level": sub.admin_level,
    #                 "parent_id": sub.parent.id if sub.parent else None,
    #                 "country_id": sub.country.id,
    #             }
    #         )
