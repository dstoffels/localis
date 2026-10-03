from abc import ABC, abstractmethod
from typing import Callable, Generic, Iterator, Mapping, TypeVar
from localis.entities import Entity
from localis.stores import Store

T = TypeVar("T", bound=Entity)
S = TypeVar("S", bound=Store, covariant=True)


class View(ABC, Generic[T, S]):
    """Base runtime view: owns id and a Store reference, other fields read from the Store by id; created on access by its ViewMap, never kept per record."""

    __slots__ = ("id", "_store")

    def __init__(self, id: int, store: S):
        self.id = id
        self._store = store

    @property
    def _idx(self) -> int:
        return self._store.id_to_idx[self.id - 1]

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def to_entity(self) -> T: ...


V = TypeVar("V", bound=View)


class ViewMap(Mapping[int, V]):
    """A store's id -> view mapping that creates each view when it's accessed, so no view object, dict entry or int key is kept per record."""

    __slots__ = ("_store", "_make")

    def __init__(self, store: Store, make: Callable[[int], V]):
        self._store = store
        self._make = make

    def __contains__(self, id: object) -> bool:
        id_to_idx = self._store.id_to_idx
        # an id excluded by a load-time filter predicate has no row
        return (
            isinstance(id, int) and 0 < id <= len(id_to_idx) and id_to_idx[id - 1] != -1
        )

    def __getitem__(self, id: int) -> V:
        if id not in self:
            raise KeyError(id)
        return self._make(id)

    def __iter__(self) -> Iterator[int]:
        return (
            id for id, idx in enumerate(self._store.id_to_idx, start=1) if idx != -1
        )

    def __len__(self) -> int:
        return len(self._store)


CV = TypeVar("CV", bound=View, covariant=True)
SV = TypeVar("SV", bound=View, covariant=True)


class CrossReferencedView(View[T, S], Generic[T, S, CV, SV]):
    """Shared by SubdivisionView/CityView; resolves references lazily against already-loaded view dicts."""

    __slots__ = ("_country_views", "_subdivision_views")

    def __init__(
        self,
        id: int,
        store: S,
        country_views: Mapping[int, CV],
        subdivision_views: Mapping[int, SV],
    ):
        super().__init__(id, store)
        self._country_views = country_views
        self._subdivision_views = subdivision_views
