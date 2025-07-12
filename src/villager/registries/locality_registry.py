from villager.registries.registry import Registry
from villager.db import LocalityModel, SubdivisionModel, CountryModel, Locality
from villager.utils import normalize


class LocalityRegistry(Registry[LocalityModel, Locality]):
    """Registry for localities."""

    osm_type_map = {
        "way": "w",
        "node": "n",
        "relation": "r",
    }

    def get(self, identifier: str) -> Locality:
        '''Fetch a locality by exact OSM type & id. Format: "[osm_type]:[osm_id]"'''
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

    def search(self, query, limit=5):
        return super().search(query, limit)

    # def get_batch(
    #     self, limit=1000, offset=0, name_prefix: str | None = None
    # ) -> list[Locality]:
    #     """Loads a batch of localities from the database."""
    #     q = self._model_cls.select()

    #     if name_prefix:
    #         q = (
    #             q.where(self._model_cls.name.startswith(name_prefix))
    #             .limit(limit)
    #             .offset(offset)
    #         )

    #     prefetched = prefetch(q, SubdivisionModel.select(), CountryModel.select())
    #     return [m.to_dto() for m in prefetched]

    def _load_cache(self, *related_models):
        return super()._load_cache(SubdivisionModel, CountryModel)

    # def _batched_prefetch(self, query, batch_size=1000):
    #     """Yields LocalityModel instances in batches, using prefetch()."""
    #     progress = 0
    #     offset = 0
    #     while True:
    #         # Select is lazily evaluated — pass the query directly to prefetch
    #         current_progress = int(offset / self.count * 100)
    #         if current_progress > progress:
    #             progress = current_progress
    #             print(f"Loading localities... {progress}%")
    #         batch_query = query.limit(batch_size).offset(offset)
    #         prefetched = list(
    #             prefetch(batch_query, SubdivisionModel.select(), CountryModel.select())
    #         )
    #         if not prefetched:
    #             break
    #         yield from prefetched
    #         offset += batch_size

    # def __iter__(self) -> Iterator[Locality]:
    #     return super().__iter__()
