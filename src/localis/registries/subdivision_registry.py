from localis.registries.registry import Registry
from localis.dtos import Subdivision
from localis.data import SubdivisionModel, CountryModel
from rapidfuzz import fuzz
import localis


class SubdivisionRegistry(Registry[SubdivisionModel, Subdivision]):
    """
    Registry for managing Subdivision entities.

    Supports exact lookup by ISO code, alpha2, or country code,
    fuzzy search by these keys, and filtering by country or country code.
    """

    ID_FIELDS = ("id", "geonames_code", "iso_code")

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
        if type is not None:
            kwargs["type"] = type
        if country is not None:
            kwargs["country"] = country
        if alt_name is not None:
            kwargs["alt_names"] = alt_name

        return super().filter(query, name, limit, **kwargs)

    def for_country(
        self,
        *,
        admin_level: int | None = 1,
        id: int = None,
        alpha2: str = None,
        alpha3: str = None,
        numeric: int = None,
        **kwargs
    ) -> list[Subdivision]:
        """Get all subdivisions for a given country by id, alpha2, alpha3 or numeric code. Can filter results by admin_level (default=1)."""
        provided = {
            k: v
            for k, v in locals().items()
            if k in ("id", "alpha2", "alpha3", "numeric") and v is not None
        }
        country = localis.countries.get(**provided)
        if country is None:
            return []

        country_field = "|".join([country.name, country.alpha2, country.alpha3])
        results: list[SubdivisionModel] = self._model_cls.select(
            SubdivisionModel.country == country_field
        )

        dtos = [r.to_dto() for r in results]

        return [d for d in dtos if d.admin_level == admin_level or admin_level == None]

    def types_for_country(
        self,
        *,
        admin_level: int | None = 1,
        id: int = None,
        alpha2: str = None,
        alpha3: str = None,
        numeric: int = None,
        **kwargs
    ) -> list[str]:
        """Fetch a list of distinct subdivision types for a given country by id, alpha2, alpha3 or numeric code. Can filter results by admin level (default=1)"""
        provided = {
            k: v
            for k, v in locals().items()
            if k in localis.countries.ID_FIELDS and v is not None
        }
        results = self.for_country(admin_level=admin_level, **provided)

        types = set(
            [
                r.type
                for r in results
                if r.type is not None and r.admin_level == admin_level
            ]
        )

        return list(types)
