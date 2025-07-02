from .loader import build_data
from .registry import CountryRegistry, SubdivisionRegistry

_raw_countries, _raw_subdivisions = build_data()

countries = CountryRegistry(_raw_countries)
subdivisions = SubdivisionRegistry(_raw_subdivisions)
