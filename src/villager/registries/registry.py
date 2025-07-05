from typing import Iterator, Generic, TypeVar
from abc import abstractmethod, ABC
import unicodedata, re
from peewee import SqliteDatabase
from ..db.models import BaseModel, DTOModel
from typing import Type

TModel = TypeVar("TModel", bound=DTOModel)
TDTO = TypeVar("TDTO")


class Registry(Generic[TModel, TDTO], ABC):
    """Abstract base registry class defining interface for lookup and search."""

    def __init__(self, db: SqliteDatabase, model: Type[TModel]):
        self._db = db
        self._model: Type[TModel] = model
        self._count: int | None = None
        self._cache: list[TDTO] | None = None

    def __iter__(self) -> Iterator[TDTO]:
        if self._cache is None:
            self._cache = self._load_cache()
        return iter(self._cache)

    def __getitem__(self, index: int) -> TDTO:
        if self._cache is None:
            self._cache = self._load_cache()
        return self._cache[index]

    def __len__(self) -> int:
        if self._count is None:
            self._count = self._model.select().count()
        return self._count

    @property
    def count(self) -> int:
        return self.__len__()

    @staticmethod
    def _normalize(s: str) -> str:
        # normalize unicode
        s = s.lower()
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
        # strip punctuation
        s = re.sub(r"[^\w\s]", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    @abstractmethod
    def get(self, identifier: str | int) -> TDTO | None:
        return None

    @abstractmethod
    def lookup(self, identifier: str) -> list[TDTO]:
        return []

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list[tuple[TDTO, float]]:
        return []

    @abstractmethod
    def _load_cache(self) -> list[TDTO]:
        return [m.to_dto() for m in self._model.select()]
