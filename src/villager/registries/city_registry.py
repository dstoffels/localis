from villager.registries.registry import Registry
from villager.db import CityModel, SubdivisionModel, CountryModel, City
from villager.utils import normalize

# from villager.literals import CountryCode, CountryName


class CityRegistry(Registry[CityModel, City]):
    """Registry for cities"""

    def __init__(self, model_cls):
        super().__init__(model_cls)
        self._order_by = "population DESC"

    osm_type_map = {
        "way": "w",
        "node": "n",
        "relation": "r",
    }

    def get(self, *, id: int = None, geonames_id: str = None, **kwargs):
        cls = self._model_cls

        field_map = {
            "id": None,
            "geonames_id": cls.geonames_id,
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
        admin1: str = None,
        admin2: str = None,
        country: str = None,
        alt_name: str = None,
        **kwargs,
    ):
        if kwargs:
            return []
        if admin1:
            kwargs["admin1"] = admin1
        if admin2:
            kwargs["admin2"] = admin2
        if country:
            kwargs["country"] = country
        if alt_name:
            kwargs["alt_names"] = alt_name

        return super().filter(query, name, limit, **kwargs)

    # def filter(
    #     self,
    #     name: str,
    #     country=None,
    #     subdivision: str = None,
    #     **kwargs,
    # ) -> list[City]:
    #     """Lookup cities by exact name, optionally filtered by country and/or subdivision."""
    #     if not name:
    #         return []

    #     norm_q = normalize(name)
    #     if country:
    #         norm_q += f" {country}"
    #     if subdivision:
    #         norm_q += f" {subdivision}"

    #     rows = self._model_cls.fts_match(norm_q, exact_match=True)
    #     return [r.dto for r in rows]

    def _sort_matches(self, matches: list, limit: int) -> list[City]:
        return [
            (row_data.dto, score)
            for row_data, score in sorted(
                matches, key=lambda r: (r[1], r[0].dto.population or 0), reverse=True
            )[:limit]
        ]
