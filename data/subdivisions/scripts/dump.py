from .utils import *


def dump_to_tsv(sub_map: SubdivisionMap):
    HEADERS = (
        # "id",
        "name",
        "alt_names",
        "geonames_code",
        "iso_code",
        "type",
        "parent_id",
        "country_id",
    )

    with open(BASE_PATH / "subdivisions.tsv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS, delimiter="\t")
        writer.writeheader()
        for sub in sub_map.get_final():
            writer.writerow(
                {
                    # "id": sub.id,
                    "name": sub.name,
                    "alt_names": "|".join(sub.alt_names),
                    "geonames_code": sub.geonames_code,
                    "iso_code": sub.iso_code,
                    "type": sub.type,
                    "parent_id": sub.parent_id,
                    "country_id": sub.country_id,
                }
            )
