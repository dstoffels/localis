from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .registries import CountryRegistry, SubdivisionRegistry, CityRegistry
    from .data import Country, Subdivision, City

from .data import Country, Subdivision, City

_countries = None
_subdivisions = None
_cities = None


def _init_countries():
    from .registries import CountryRegistry

    global _countries
    if _countries is None:
        _countries = CountryRegistry()

        import sys

        sys.modules[__name__].countries = _countries
    return _countries


def _init_subdivisions():
    from .registries import SubdivisionRegistry

    global _subdivisions
    if _subdivisions is None:
        _subdivisions = SubdivisionRegistry(countries=_init_countries())
        import sys

        sys.modules[__name__].subdivisions = _subdivisions
    return _subdivisions


def _init_cities():
    from .registries import CityRegistry

    global _cities
    if _cities is None:
        _cities = CityRegistry(
            countries=_init_countries(), subdivisions=_init_subdivisions()
        )
        import sys

        sys.modules[__name__].cities = _cities
    return _cities


def __getattr__(name):
    if name == "countries":
        return _init_countries()
    elif name == "subdivisions":
        return _init_subdivisions()
    elif name == "cities":
        return _init_cities()
    raise AttributeError(f"module {__name__} has no attribute {name}")


__all__ = ["Country", "Subdivision", "City", "countries", "subdivisions", "cities"]
