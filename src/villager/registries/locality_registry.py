from .registry import Registry
from ..db import LocalityModel, SubdivisionModel, CountryModel
from ..types import Locality
from peewee import prefetch
from typing import Iterator


class LocalityRegistry(Registry[LocalityModel, Locality]):
    """Registry for localities.

    WARNING: It is not recommened to use this registry as an iterable, as it will load all localities into memory. This is very heavy and slow, iterate at your own risk!

    Alternatively, get_batch allows you to load a filtered slice of localities by name prefix.
    """

    def __init__(self, model_cls, dto_cls):
        super().__init__(model_cls, dto_cls)

    def get(self, identifier: int) -> Locality:
        if isinstance(identifier, str):
            try:
                identifier = int(identifier)
            except:
                return None
        return self._model_cls.get_or_none(LocalityModel.osm_id == identifier)

    def lookup(self, identifier):
        return super().lookup(identifier)

    def search(self, query, limit=5):
        return super().search(query, limit)

    def _build_sql(self):
        return super()._build_sql()

    def get_batch(
        self, limit=1000, offset=0, name_prefix: str | None = None
    ) -> list[Locality]:
        """Loads a batch of localities from the database."""
        q = self._model_cls.select()

        if name_prefix:
            q = (
                q.where(self._model_cls.name.startswith(name_prefix))
                .limit(limit)
                .offset(offset)
            )

        prefetched = prefetch(q, SubdivisionModel.select(), CountryModel.select())
        return [m.to_dto() for m in prefetched]

    def _load_cache(self, *related_models):
        return super()._load_cache(SubdivisionModel, CountryModel)

    def _batched_prefetch(self, query, batch_size=1000):
        """Yields LocalityModel instances in batches, using prefetch()."""
        progress = 0
        offset = 0
        while True:
            # Select is lazily evaluated — pass the query directly to prefetch
            current_progress = int(offset / self.count * 100)
            if current_progress > progress:
                progress = current_progress
                print(f"Loading localities... {progress}%")
            batch_query = query.limit(batch_size).offset(offset)
            prefetched = list(
                prefetch(batch_query, SubdivisionModel.select(), CountryModel.select())
            )
            if not prefetched:
                break
            yield from prefetched
            offset += batch_size

    # def __iter__(self) -> Iterator[Locality]:
    #     return super().__iter__()
