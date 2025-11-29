from data.utils import *
import csv


def dump_to_tsv(countries: dict[str, CountryData]):
    headers = (
        "name",
        "official_name",
        "alt_names",
        "alpha2",
        "alpha3",
        "numeric",
        "flag",
        "search_tokens",
    )

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
