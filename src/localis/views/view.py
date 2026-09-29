from abc import ABC, abstractmethod
from typing import Generic, TypeVar, TYPE_CHECKING
from localis.entities import Entity
from localis.stores import Store

if TYPE_CHECKING:
    from .country_view import CountryView
    from .subdivision_view import SubdivisionView

T = TypeVar("T", bound=Entity)


class View(ABC, Generic[T]):
    """Base runtime view: owns id and a Store reference; other fields read from Store by (id - 1)."""

    __slots__ = ("id", "_store")

    def __init__(self, id: int, store: Store):
        self.id = id
        self._store = store

    @property
    def _idx(self) -> int:
        return self.id - 1

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def to_entity(self) -> T: ...


class CrossReferencedView(View[T]):
    """Shared by SubdivisionView/CityView; resolves references lazily against already-loaded view dicts."""

    __slots__ = ("_country_views", "_subdivision_views")

    def __init__(
        self,
        id: int,
        store: Store,
        country_views: dict[int, "CountryView"],
        subdivision_views: dict[int, "SubdivisionView"],
    ):
        super().__init__(id, store)
        self._country_views = country_views
        self._subdivision_views = subdivision_views
