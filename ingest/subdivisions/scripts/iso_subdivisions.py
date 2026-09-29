from ingest.utils import SUBDIVISIONS_RAW_PATH
from ingest.countries import CountryModel
from ingest.subdivisions import SubdivisionModel
import json


def load_iso_subs(countries: dict[str, CountryModel]) -> dict[str, SubdivisionModel]:
    """Parses ISO 3166-2 subdivisions from Debian's iso-codes, the authoritative source."""
    print("Loading ISO subdivisions...")
    iso_subs: dict[str, SubdivisionModel] = {}

    with open(SUBDIVISIONS_RAW_PATH / "iso_3166-2.json", "r", encoding="utf-8") as f:
        entries: list[dict] = json.load(f)["3166-2"]

    for entry in entries:
        iso_code = entry["code"]
        alpha2 = iso_code.split("-")[0]
        parent_iso_code = entry.get("parent")
        admin_level = 1 if not parent_iso_code else 2

        country = countries.get(alpha2)
        if not country:
            raise ValueError(f"Country not found for alpha2: {alpha2}")

        subdivision = SubdivisionModel(
            id=0,  # temporary, will be set when all loaded
            name=entry["name"],
            country=country,
            type=entry["type"],
            iso_code=iso_code,
            admin_level=admin_level,
            aliases=[],  # enriched separately, see merge_ipregistry.py
            geonames_code=None,  # may be set later if merged with GeoNames subdivision
            parent=parent_iso_code,  # temporarily set to iso_code string to map later once all iso subs are loaded
        )

        # set temporary id to hashid for later mapping
        subdivision.set_hashid()
        subdivision.id = subdivision.hashid

        iso_subs[iso_code] = subdivision

    # parent stays as the raw iso_code string here; SubdivisionMap.refresh()
    # resolves it to the actual object once merging/resolution has settled,
    # since the object it should point to may be discarded during merge.
    return iso_subs
