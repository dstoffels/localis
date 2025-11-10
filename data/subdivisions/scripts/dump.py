from .utils import *


def concat_country(country: CountryDTO) -> str:
    return f"{country.name}|{country.alpha2}{f'|{country.alpha3}' if country.alpha3 else ''}"


def dump_to_tsv(countries: dict[str, CountryDTO], sub_map: SubdivisionMap):
    HEADERS = (
        "id",
        "name",
        "alt_names",
        "geonames_code",
        "iso_code",
        "country",
        "type",
        "parent_rowid",
    )

    with open(BASE_PATH / "subdivisions.tsv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS, delimiter="\t")
        writer.writeheader()
        for sub in sub_map.get_final():
            writer.writerow(
                {
                    "id": sub.id,
                    "name": sub.name,
                    "alt_names": "|".join(sub.alt_names),
                    "geonames_code": sub.geonames_code,
                    "iso_code": sub.iso_code,
                    "country": concat_country(countries[sub.country_alpha2]),
                    "type": sub.type,
                    "parent_rowid": sub.parent_id,
                }
            )
