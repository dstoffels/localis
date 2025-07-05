from .registry import Registry
from ..db import LocalityModel, SubdivisionModel, CountryModel
from ..types import Locality
from peewee import prefetch
from peewee import fn


class LocalityRegistry(Registry[LocalityModel, Locality]):
    """Registry for localities. WARNING: using this registry as an iterable will load all localities into memory. This is very heavy and slow."""

    def __init__(self, db, model):
        super().__init__(db, model)

    def get(self, identifier: int) -> Locality:
        if isinstance(identifier, str):
            try:
                identifier = int(identifier)
            except:
                return None
        return self._model.get_or_none(LocalityModel.osm_id == identifier)

    def lookup(self, identifier):
        return super().lookup(identifier)

    def search(self, query, limit=5):
        return super().search(query, limit)

    def _load_cache(self) -> list[Locality]:
        q = self._model.select()
        models = list(prefetch(q, SubdivisionModel.select(), CountryModel.select()))
        return [m.to_dto() for m in models]
