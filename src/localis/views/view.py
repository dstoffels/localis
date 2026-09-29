from abc import ABC, abstractmethod
from typing import Generic, TypeVar, TYPE_CHECKING
from localis.entities import Entity
from localis.stores import Store

if TYPE_CHECKING:
    from .country_view import CountryView
    from .subdivision_view import SubdivisionView

T = TypeVar("T", bound=Entity)


class View(ABC, Generic[T]):
    """Base for every entity's runtime view: owns only its id and a reference to
    the shared columnar Store, every other field is a computed property reading
    from that Store by (id - 1)."""

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
    """Shared by SubdivisionView and CityView, which both resolve references
    lazily against already-loaded country and subdivision view dicts, so load
    order never matters."""

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
