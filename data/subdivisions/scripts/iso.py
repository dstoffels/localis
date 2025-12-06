from data.utils import *
from data.subdivisions.utils import SubdivisionMap
from data.subdivisions.utils import dedupe
import csv
from localis.models import CountryModel, SubdivisionModel


def load_iso_subs(
    countries: dict[str, CountryModel], submap=SubdivisionMap
) -> dict[int, SubdivisionModel]:
    print("Loading ISO subdivisions...")
    with open(SUB_SRC_PATH / "iso-3166-2.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        iso_subs: dict[int, SubdivisionModel] = {}  # cache

        for row in reader:
            local_name = row["localVariant"]  # canonical name if present
            iso_name = row["name"]  # canonical name if no local variant
            alpha2 = row["country_code"]
            iso_code = row["iso_code"]
            parent_iso_code = row.get("parent_iso_code", None)
            admin_level = 1 if not parent_iso_code else 2

            # Assign names, generate ascii alt names
            name = local_name or iso_name

            alt_name = iso_name if local_name else None

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

        # Second pass to resolve parents now that all iso subs are loaded
        for iso_sub in iso_subs.values():
            parent_iso_code = iso_sub.parent
            iso_sub.parent = iso_subs.get(parent_iso_code, None)

        return iso_subs
