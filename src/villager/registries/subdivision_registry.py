from .registry import Registry
from ..db.dtos import Subdivision
from typing import Callable, Optional
from ..db import SubdivisionModel, CountryModel

# from ..literals import CountryCode, CountryName, CountryNumeric
from rapidfuzz import fuzz
from villager.utils import normalize


class SubdivisionRegistry(Registry[SubdivisionModel, Subdivision]):
    """
    Registry for managing Subdivision entities.

    Supports exact lookup by ISO code, alpha2, or country code,
    fuzzy search by these keys, and filtering by country or country code.
    """

    def get(self, *, id: int = None, iso_code: str = None, geonames_code: str = None):
        cls = self._model_cls

        field_map = {
            "id": None,
            "iso_code": cls.iso_code,
            "geonames_code": cls.geonames_code,
        }

        model = None
        for arg, field in field_map.items():
            val = locals()[arg]
            if val is not None:
                model = cls.get_by_id(val) if arg == "id" else cls.get(field == val)

        return model.to_dto() if model is not None else None

    # def get(self, iso_code: str) -> Subdivision:
    #     """Fetch a subdivision by exact iso code."""
    #     if not iso_code:
    #         return None

    #     iso_code = iso_code.upper().strip()

    #     row = self._model_cls.get(SubdivisionModel.iso_code == iso_code)

    #     if row:
    #         return row.dto

    # def filter(self, name: str, country="", **kwargs) -> list[Subdivision]:
    #     """Lookup subdivisions by exact name, optionally filtered by country."""
    #     if not name:
    #         return []

    #     norm_q = normalize(name)
    #     if country:
    #         norm_q = f"{norm_q} {country}"

    #     rows = self._model_cls.fts_match(norm_q, exact_match=True)

    #     return [r.dto for r in rows]

    def by_country(self, country_code) -> list[Subdivision]:
        """Fetch all subdivisions for a given country by code."""
        if not country_code:
            return []
        c = CountryModel.get(
            (CountryModel.alpha2 == country_code)
            | (CountryModel.alpha3 == country_code)
        )
        rows = self._model_cls.select(SubdivisionModel.country_id == c.id)
        return [r.dto for r in rows]

    def get_categories(self, country_code) -> list[str]:
        """Fetch distinct subdivision categories for a given country by code (e.g. "state", "province"). Helpful for dynamic dropdowns."""
        if not country_code:
            return []
        cats = set()
        c = CountryModel.get(
            (CountryModel.alpha2 == country_code)
            | (CountryModel.alpha3 == country_code)
        )

        rows = self._model_cls.select(SubdivisionModel.country_id == c.id)
        for r in rows:
            cats.add(r.dto.category)
        return list(cats)
