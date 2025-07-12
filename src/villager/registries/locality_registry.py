from .registry import Registry
from ..db import LocalityModel, SubdivisionModel, CountryModel
from ..db.dtos import Locality


class LocalityRegistry(Registry[LocalityModel, Locality]):
    """Registry for localities."""

    def get(self, identifier: int) -> Locality:
        if isinstance(identifier, str):
            try:
                identifier = int(identifier)
            except:
                return None
        return self._model_cls.get(LocalityModel.osm_id == identifier)

    def lookup(self, identifier):
        return super().lookup(identifier)

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
