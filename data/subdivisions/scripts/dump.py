from ..utils import *
import gzip
import json
from collections import defaultdict


def dump_to_tsv(sub_map: SubdivisionMap):
    subdivisions = sub_map.get_final()

    with gzip.open(
        FIXTURE_PATH / "subdivisions_search_index.gz", "wt", compresslevel=9
    ) as f:
        search_index = defaultdict(list)
        for sub in subdivisions:
            for trigram in sub.extract_trigrams():
                search_index[trigram].append(sub.iso_code)

    HEADERS = (
        "name",
        "alt_names",
        "geonames_code",
        "iso_code",
        "type",
        "parent_id",
        "country_id",
    )

    with open(
        FIXTURE_PATH / "subdivisions.tsv",
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS, delimiter="\t")
        writer.writeheader()
        for sub in sub_map.get_final():
            writer.writerow(
                {
                    "name": sub.name,
                    "alt_names": "|".join(sub.alt_names),
                    "geonames_code": sub.geonames_code,
                    "iso_code": sub.iso_code,
                    "type": sub.type,
                    "parent_id": sub.parent_id,
                    "country_id": sub.country_id,
                }
            )
