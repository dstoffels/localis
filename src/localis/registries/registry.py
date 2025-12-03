from typing import Iterator, Generic, TypeVar
from localis.models import Model
from abc import ABC
from localis.models import DTO
from pathlib import Path
import gzip
import pickle
from localis.indexes import FilterIndex, SearchIndex, LookupIndex
from localis.utils import ModelData

T = TypeVar("DTO", bound=DTO)


class Registry(Generic[T], ABC):
    """"""

    REGISTRY_NAME: str = ""
    _MODEL_CLS: type[Model]

    def __init__(self, **kwargs):
        # ---------- Lazy loaded attributes ---------- #

        # For speed, the cache stores raw data rows as tuples, and the model/dto instances are created on demand
        self._cache: dict[int, ModelData] | None = None
        self._lookup_index: LookupIndex | None = None
        self._filter_index: FilterIndex | None = None
        self._search_index: SearchIndex | None = None

    @property
    def _data_path(self) -> Path:
        return Path(__file__).parent.parent / "data" / self.REGISTRY_NAME

    @property
    def _data_filepath(self) -> Path:
        return self._data_path / f"{self.REGISTRY_NAME}.pkl.gz"

    @property
    def _lookup_filepath(self) -> Path:
        return self._data_path / f"{self.REGISTRY_NAME}_lookup_index.pkl.gz"

    @property
    def _filter_filepath(self) -> Path:
        return self._data_path / f"{self.REGISTRY_NAME}_filter_index.pkl.gz"

    @property
    def _search_filepath(self) -> Path:
        return self._data_path / f"{self.REGISTRY_NAME}_search_index.pkl.gz"

    @property
    def count(self) -> int:
        return len(self.cache)

    # ----------- LAZY LOADERS ----------- #
    @property
    def cache(self) -> dict[int, ModelData]:
        if self._cache is None:
            if not self._data_filepath.exists():
                raise FileNotFoundError(f"Data file not found: {self._data_filepath}")

            try:
                with gzip.open(self._data_filepath, "rb") as f:
                    self._cache = pickle.load(f)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load data file: {self._data_filepath}"
                ) from e
        return self._cache

    @property
    def lookup_index(self) -> LookupIndex:
        if self._lookup_index is None:
            self._lookup_index = LookupIndex(
                model_cls=self._MODEL_CLS,
                cache=self.cache,
                filepath=self._lookup_filepath,
            )
        return self._lookup_index

    @property
    def filter_index(self) -> FilterIndex:
        if self._filter_index is None:
            self._filter_index = FilterIndex(
                model_cls=self._MODEL_CLS,
                cache=self.cache,
                filepath=self._filter_filepath,
            )
        return self._filter_index

    @property
    def search_index(self) -> SearchIndex:
        if self._search_index is None:
            self._search_index = SearchIndex(
                model_cls=self._MODEL_CLS,
                cache=self.cache,
                filepath=self._search_filepath,
            )
        return self._search_index

    def __iter__(self) -> Iterator[T]:
        return iter(self.cache.values())

    def __getitem__(self, index: int) -> T:
        return list(self.cache.values())[index]

    def __len__(self) -> int:
        return len(self.cache)

    def _resolve_model(self, id: int) -> T | None:
        """Resolves a DTO instance from its ID, resolves dependency DTOs, and returns the final DTO for the user."""
        row = self.cache.get(id)
        if not row:
            return None

        flat_model = self._MODEL_CLS(*row)
        return flat_model.dto

    # ----------- API METHODS ----------- #

    # ----------- GET ----------- #

    def get(self, id: int) -> T | None:
        """Get by localis ID."""
        return self._resolve_model(id)

    # ----------- LOOKUP ----------- #

    def lookup(self, identifier: str | int) -> T | None:
        """Fetches a single item by one of its other unique identifiers (use .get() for localis ID)."""

        model_id = self.lookup_index.get(identifier)
        return self._resolve_model(model_id)

    # ----------- FILTER ----------- #

    def filter(self, *, name: str = None, limit: int = None, **kwargs) -> list[T]:
        """Filter by exact matches on specified fields with AND logic when filtering by multiple fields. Case insensitive."""
        kwargs["name"] = name

        filter_kws = {k: v for k, v in kwargs.items() if v is not None}

        results: set[int] = None

        # short circuit
        if not filter_kws:
            return []

        for key, value in filter_kws.items():
            matches = self.filter_index.filter(filter_kw=key, field_value=value)

            # short circuit if any field fails to match, all or nothing
            if not matches:
                return []

            if results is None:
                results = matches
            else:
                results &= matches
        results_list = [self._resolve_model(id) for id in list(results)[:limit]]
        results_list.sort(key=lambda r: r.name)  # sort alphabetically by name
        return results_list

    # ----------- SEARCH ----------- #

    def search(self, query: str, limit: int = None, **kwargs) -> list[tuple[T, float]]:
        return self.search_index.search(query=query, limit=limit)
