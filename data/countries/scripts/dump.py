from .utils import *
import csv


def dump_to_tsv(countries: dict[str, CountryDTO]):
    headers = (
        # "id",
        "name",
        "official_name",
        "alt_names",
        "alpha2",
        "alpha3",
        "numeric",
        "flag",
    )

    with open(
        BASE_PATH.parent.parent / "src/localis/data/countries.tsv",
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(headers)
        for c in countries.values():
            writer.writerow(c.dump())
