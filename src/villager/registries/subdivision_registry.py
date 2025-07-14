from .registry import Registry
from ..db.dtos import Subdivision
from typing import Callable, Optional
from ..db import SubdivisionModel, CountryModel
from ..literals import CountryCode, CountryName, CountryNumeric
from rapidfuzz import fuzz
from villager.utils import normalize


class SubdivisionRegistry(Registry[SubdivisionModel, Subdivision]):
    """
    Registry for managing Subdivision entities.

    Supports exact lookup by ISO code, alpha2, or country code,
    fuzzy search by these keys, and filtering by country or country code.
    """

    def get(self, iso_code: str) -> Subdivision:
        """Fetch a subdivision by exact iso code."""
        if not iso_code:
            return None

        iso_code = iso_code.upper().strip()

        row = self._model_cls.get(SubdivisionModel.iso_code == iso_code)

        if row:
            return row.dto

    def lookup(
        self, name: str, country: CountryCode | CountryName = "", **kwargs
    ) -> list[Subdivision]:
        """Lookup subdivisions by exact name, optionally filtered by country."""
        if not name:
            return []

        name = normalize(name)
        if country:
            c = CountryModel.get(
                (CountryModel.alpha2 == country)
                | (CountryModel.alpha3 == country)
                | (CountryModel.normalized_name == normalize(country))
            )
            rows = self._model_cls.select(
                (SubdivisionModel.normalized_name == name)
                & (SubdivisionModel.country_id == c.id)
            )
        else:
            rows = self._model_cls.select(SubdivisionModel.normalized_name == name)

        return [r.dto for r in rows]

    def search(
        self, query: str, limit=5, country: CountryCode | CountryName = None, **kwargs
    ) -> list[Subdivision]:
        """Fuzzy search subdivisions, optionally filtered by country."""

        if not query:
            return []

        # reset
        self._addl_fts_clause = ""

        if country:
            country = normalize(country)
            self._addl_fts_clause = f"AND (country = '{country}' OR country_alpha2 = '{country}' OR country_alpha3 = '{country}')"

        return super().search(query, limit)

    def by_country(self, country_code: CountryCode) -> list[Subdivision]:
        """Fetch all subdivisions for a given country by code."""
        if not country_code:
            return []
        c = CountryModel.get(
            (CountryModel.alpha2 == country_code)
            | (CountryModel.alpha3 == country_code)
        )
        rows = self._model_cls.select(SubdivisionModel.country_id == c.id)
        return [r.dto for r in rows]

    def get_categories(self, country_code: CountryCode) -> list[str]:
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
