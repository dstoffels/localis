from typing import Iterator, Generic, TypeVar
from abc import ABC
from typing import Type
from villager.data import DTO, Model
from villager.search import FuzzySearch

TModel = TypeVar("TModel", bound=Model)
TDTO = TypeVar("TDTO", bound=DTO)


class Registry(Generic[TModel, TDTO], ABC):
    """Abstract base registry class defining interface for lookup and search."""

    ID_FIELDS: tuple[str] = ()

    SEARCH_FIELD_WEIGHTS: dict[str, float] = {}
    SEARCH_ORDER_FIELDS: list[str] = []
    """Override to provide the fields for search scoring."""

    def __init__(self, model_cls: Type[TModel]):
        self._model_cls: Type[TModel] = model_cls
        self._count: int | None = None
        self._cache: list[TDTO] = None
        self._order_by: str = ""
        self._addl_search_attrs: list[str] = []

    @property
    def cache(self):
        if self._cache is None:
            self._cache = [m.to_dto() for m in self._model_cls.select()]
        return self._cache

    def __iter__(self) -> Iterator[TDTO]:
        return iter(self.cache)

    def __getitem__(self, index: int | slice) -> TDTO | list[TDTO]:
        return self.cache[index]

    def __len__(self) -> int:
        if self._count is None:
            self._count = self._model_cls.count()
        return self._count

    @property
    def count(self) -> int:
        return self.__len__()

    def get(self, *, id: int | None = None, **kwargs) -> TDTO | None:
        return None

    def filter(
        self, query: str = None, name: str = None, limit: int = None, **kwargs
    ) -> list[TDTO]:
        if kwargs:
            if name:
                kwargs.update({"name": name})
            results = self._model_cls.fts_match(
                field_queries=kwargs, order_by=["rank"], limit=limit
            )

        elif name:
            results = self._model_cls.fts_match(
                field_queries={"name": name}, order_by=["rank"], limit=limit
            )
        elif query:
            results = self._model_cls.fts_match(query, order_by=["rank"], limit=limit)
        else:
            return []

        return [r.to_dto() for r in results]

    def search(self, query: str, limit=None, **kwargs) -> list[tuple[TDTO, float]]:
        if not query:
            return []

        search = FuzzySearch(
            query,
            self._model_cls,
            self.SEARCH_FIELD_WEIGHTS,
            self.SEARCH_ORDER_FIELDS,
            limit,
        )

        return search.run()

    def _sort_matches(self, matches: list, limit: int) -> list[TDTO]:
        return [
            (row_data.dto, score)
            for row_data, score in sorted(matches, key=lambda r: r[1], reverse=True)[
                :limit
            ]
        ]
