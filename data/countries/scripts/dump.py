from .utils import *
import csv


def dump_to_tsv(countries: dict[str, CountryDTO]):
    headers = (
        "name",
        "official_name",
        "alpha2",
        "alpha3",
        "numeric",
        "alt_names",
        "flag",
    )

    with open(BASE_PATH / "countries.tsv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(headers)
        for c in countries.values():
            writer.writerow(c.dump())
