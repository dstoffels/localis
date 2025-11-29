from data.utils import *
from data.subdivisions.utils import dedupe
import csv


def load_iso_subs(countries: dict[str, CountryData]) -> dict[int, SubdivisionData]:
    print("Loading ISO subdivisions...")
    with open(SUB_SRC_PATH / "iso-3166-2.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        iso_subs: dict[int, SubdivisionData] = {}  # cache

        for row in reader:
            local_name = row["localVariant"]  # canonical name if present
            iso_name = row["name"]  # canonical name if no local variant
            alpha2 = row["country_code"]
            iso_code = row["iso_code"]
            parent_iso_code = row.get("parent_iso_code", None)
            parent_code = parent_iso_code.replace("-", ".") if parent_iso_code else None
            admin_level = 1 if not parent_code else 2

            # Assign names, generate ascii alt names
            name = local_name or iso_name

            alt_name = iso_name if local_name else None
            ascii_alt_name = normalize(alt_name).title() if alt_name else None

            country = countries.get(alpha2)
            if not country:
                raise ValueError(f"Country not found for alpha2: {alpha2}")

            if iso_code not in iso_subs:
                # create new subdivision and cache
                subdivision = SubdivisionData(
                    name=name,
                    country_id=country.id,
                    country_alpha2=country.alpha2,
                    country_alpha3=country.alpha3,
                    country_name=country.name,
                    parent_id=parent_code,
                    type=row["category"],
                    iso_code=iso_code,
                    admin_level=admin_level,
                )

                iso_subs[iso_code] = subdivision
            else:
                # merge into existing subdivision if iso code already exists in cache
                subdivision = iso_subs[iso_code]

            # build alt names
            for n in [name, alt_name]:
                if n and n not in subdivision.alt_names and n != subdivision.name:
                    subdivision.alt_names.append(n)

            subdivision.alt_names = dedupe(subdivision.alt_names)

        return iso_subs
