from abc import ABC, abstractmethod
from typing import Generic, Mapping, TypeVar
from localis.entities import Entity
from localis.stores import Store

T = TypeVar("T", bound=Entity)
S = TypeVar("S", bound=Store, covariant=True)


class View(ABC, Generic[T, S]):
    """Base runtime view: owns id and a Store reference; other fields read from Store by (id - 1)."""

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
