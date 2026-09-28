from data.utils.paths import SUBDIVISIONS_RAW_PATH
from data.subdivisions.utils.strings import dedupe
import csv
from localis.models import CountryModel, SubdivisionModel


def load_iso_subs(countries: dict[str, CountryModel]) -> dict[int, SubdivisionModel]:
    print("Loading ISO subdivisions...")
    with open(SUBDIVISIONS_RAW_PATH / "iso-3166-2.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        iso_subs: dict[str, SubdivisionModel] = {}  # cache

        for row in reader:
            name = row["subdivision_name"]
            local_variant = row["localVariant"]
            alpha2 = row["#country_code_alpha2"]
            iso_code = row["subdivision_code_iso3166-2"]
            parent_iso_code = row.get("parent_subdivision", None)
            admin_level = 1 if not parent_iso_code else 2

            # Assign names, generate ascii alt names

            alt_name = local_variant or None

            country = countries.get(alpha2)
            if not country:
                raise ValueError(f"Country not found for alpha2: {alpha2}")

            if iso_code not in iso_subs:
                # create new subdivision and cache
                subdivision = SubdivisionModel(
                    id=0,  # temporary, will be set when all loaded
                    name=name,
                    country=country,
                    type=row["category"],
                    iso_code=iso_code,
                    admin_level=admin_level,
                    aliases=[alt_name] if alt_name else [],
                    geonames_code=None,  # may be set later if merged with GeoNames subdivision
                    parent=parent_iso_code,  # temporarily set to iso_code string to map later once all iso subs are loaded
                )

                # set temporary id to hashid for later mapping
                subdivision.id = subdivision.hashid

                iso_subs[iso_code] = subdivision
            else:
                # merge into existing subdivision if iso code already exists in cache
                subdivision = iso_subs[iso_code]

            # build aliases
            for n in [name, alt_name]:
                if n and n not in subdivision.aliases and n != subdivision.name:
                    subdivision.aliases.append(n)

            subdivision.aliases = dedupe(subdivision.aliases)

        # parent stays as the raw iso_code string here; SubdivisionMap.refresh()
        # resolves it to the actual object once merging/resolution has settled,
        # since the object it should point to may be discarded during merge.
        return iso_subs
