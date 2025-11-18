from villager.registries.registry import Registry
from villager.dtos import Subdivision
from villager.db import SubdivisionModel, CountryModel
from rapidfuzz import fuzz
from villager.utils import normalize


class SubdivisionRegistry(Registry[SubdivisionModel, Subdivision]):
    """
    Registry for managing Subdivision entities.

    Supports exact lookup by ISO code, alpha2, or country code,
    fuzzy search by these keys, and filtering by country or country code.
    """

    SEARCH_FIELD_WEIGHTS = {"name": 1.0, "alt_names": 0.4, "country": 0.33}

    def get(
        self,
        *,
        id: int = None,
        iso_code: str = None,
        geonames_code: str = None,
        **kwargs
    ):
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

    def filter(
        self,
        query: str = None,
        name: str = None,
        limit: int = None,
        type: str = None,
        country: str = None,
        alt_name: str = None,
        **kwargs
    ):
        if kwargs:
            return []
        if type:
            kwargs["type"] = type
        if country:
            kwargs["country"] = country
        if alt_name:
            kwargs["alt_names"] = alt_name

        return super().filter(query, name, limit, **kwargs)

    @property
    def search_field_weights(self):
        pass

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
