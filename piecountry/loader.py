from .parser import load_countries, load_subdivisions
from .types import Country, Subdivision
from dataclasses import replace
from collections import defaultdict


def build_data() -> tuple[list[Country], list[Subdivision]]:
    countries = load_countries()
    countries_by_alpha2 = {c.alpha2: c for c in countries}
    subdivisions = load_subdivisions(countries_by_alpha2)

    # Backfill subdivisions into country objects
    subs_by_country = defaultdict(list)
    for sub in subdivisions:
        subs_by_country[sub.country_code].append(sub)

    countries_with_subs = [
        replace(c, subdivisions=subs_by_country.get(c.alpha2, [])) for c in countries
    ]

    return countries_with_subs, subdivisions
