# src/localis/__init__.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .registries import CountryRegistry, SubdivisionRegistry, CityRegistry
    from .data import Country, Subdivision, City

from .data import Country, Subdivision, City

# placeholders for type checkers and autocomplete
countries: "CountryRegistry"
subdivisions: "SubdivisionRegistry"
cities: "CityRegistry"

# internal private variables
_countries = None
_subdivisions = None
_cities = None


def _init_countries() -> "CountryRegistry":
    global _countries
    if _countries is None:
        from .registries import CountryRegistry

        _countries = CountryRegistry()
    return _countries


def _init_subdivisions() -> "SubdivisionRegistry":
    global _subdivisions
    if _subdivisions is None:
        from .registries import SubdivisionRegistry

        _subdivisions = SubdivisionRegistry(countries=_init_countries())
    return _subdivisions


def _init_cities() -> "CityRegistry":
    global _cities
    if _cities is None:
        from .registries import CityRegistry

        _cities = CityRegistry(
            countries=_init_countries(), subdivisions=_init_subdivisions()
        )
    return _cities


# module-level lazy attribute access
def __getattr__(name):
    if name == "countries":
        return _init_countries()
    if name == "subdivisions":
        return _init_subdivisions()
    if name == "cities":
        return _init_cities()
    raise AttributeError(f"module {__name__} has no attribute {name}")


# inform static tools about what exists
__all__ = ["Country", "Subdivision", "City", "countries", "subdivisions", "cities"]
