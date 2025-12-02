from data.utils import *
import csv
import json
from collections import defaultdict
import gzip


def dump(countries: dict[str, CountryData]):
    # Dump country search index
    with gzip.open(
        FIXTURE_PATH / "country_search_index.json.gz", "wt", compresslevel=9
    ) as f:
        search_index = defaultdict(list)
        for c in countries.values():
            for trigram in c.extract_trigrams():
                search_index[trigram].append(c.id)
        json.dump(search_index, f, ensure_ascii=False, indent=2, separators=(",", ": "))

    headers = (
        "name",
        "official_name",
        "alt_names",
        "alpha2",
        "alpha3",
        "numeric",
        "flag",
    )

    # Dump country data file
    with open(
        FIXTURE_PATH / "countries.tsv",
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(headers)
        for c in countries.values():
            writer.writerow(c.dump())
