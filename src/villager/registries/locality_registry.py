from villager.registries.registry import Registry
from villager.db import LocalityModel, SubdivisionModel, CountryModel, Locality
from villager.utils import normalize
from villager.literals import CountryCode, CountryName


class LocalityRegistry(Registry[LocalityModel, Locality]):
    """Registry for localities."""

    osm_type_map = {
        "way": "w",
        "node": "n",
        "relation": "r",
    }

    def get(self, identifier: str) -> Locality:
        '''Fetch a locality by exact OSM type & id. Format: "[type]:[id]"'''
        if not identifier:
            return None

        type, id = identifier.strip().split(":")

        type = self.osm_type_map.get(type.lower(), type)

        row = self._model_cls.get(
            (LocalityModel.osm_id == id) & (LocalityModel.osm_type == type)
        )
        return row.dto

    def lookup(self, name: str, **kwargs) -> list[Locality]:
        """Lookup localities by exact name."""
        if not name:
            return []

        name = normalize(name)

        rows = self._model_cls.select(LocalityModel.normalized_name == name)
        return [r.dto for r in rows]
