from array import array
from pathlib import Path
from dataclasses import dataclass
from .model import DTO, Model


@dataclass(slots=True)
class CountryBase(DTO):
    alpha2: str
    alpha3: str | None


@dataclass(slots=True)
class Country(CountryBase):
    official_name: str
    aliases: list[str]
    numeric: int | None
    flag: str | None


@dataclass(slots=True)
class CountryModel(Country, Model):
    LOOKUP_FIELDS = ("alpha2", "alpha3", "numeric")
    FILTER_FIELDS = {"name": ("name", "official_name", "aliases")}
    SEARCH_FIELDS = {
        "name": 1.0,
        "official_name": 1.0,
        "aliases": 1.0,
    }

    def to_row(self) -> tuple[str | int | None]:
        data = self.to_dict()
        data["aliases"] = "|".join(self.aliases)
        data.pop("id")
        return tuple(data.values())

    @classmethod
    def from_row(cls, id: int, row: list[str | int | None], **kwargs) -> "CountryModel":
        ALIAS_IDX = 4
        NUMERIC_IDX = 5

        row[ALIAS_IDX] = [a for a in row[ALIAS_IDX].split("|") if a]
        row[NUMERIC_IDX] = int(row[NUMERIC_IDX]) if row[NUMERIC_IDX] else None

        return cls(id, *row)


class CountryStore:
    """Columnar storage for all countries' field data, shared by every CountryView."""

    __slots__ = (
        "names",
        "alpha2s",
        "alpha3s",
        "official_names",
        "aliases",
        "numerics",
        "flags",
    )

    def __init__(self):
        self.names: list[str] = []
        self.alpha2s: list[str] = []
        self.alpha3s: list[str] = []
        self.official_names: list[str] = []
        self.aliases: list[list[str]] = []
        self.numerics = array("i")  # -1 sentinel for None
        self.flags: list[str] = []

    def append(
        self,
        name: str,
        alpha2: str,
        alpha3: str,
        official_name: str,
        alias_list: list[str],
        numeric: int | None,
        flag: str,
    ) -> None:
        self.names.append(name)
        self.alpha2s.append(alpha2)
        self.alpha3s.append(alpha3)
        self.official_names.append(official_name)
        self.aliases.append(alias_list)
        self.numerics.append(numeric if numeric is not None else -1)
        self.flags.append(flag)

    def __len__(self) -> int:
        return len(self.names)


class CountryView:
    """Lightweight runtime view over CountryStore; used for Registry._cache instead of
    CountryModel, which stays a plain mutable dataclass for ingestion. Each instance owns
    only its id, every field is read from the shared columnar store on access."""

    __slots__ = ("id", "_store")

    SEARCH_FIELDS = CountryModel.SEARCH_FIELDS

    def __init__(self, id: int, store: CountryStore):
        self.id = id
        self._store = store

    @property
    def _idx(self) -> int:
        return self.id - 1

    @property
    def name(self) -> str:
        return self._store.names[self._idx]

    @property
    def alpha2(self) -> str:
        return self._store.alpha2s[self._idx]

    @property
    def alpha3(self) -> str:
        return self._store.alpha3s[self._idx]

    @property
    def official_name(self) -> str:
        return self._store.official_names[self._idx]

    @property
    def aliases(self) -> list[str]:
        return self._store.aliases[self._idx]

    @property
    def numeric(self) -> int | None:
        v = self._store.numerics[self._idx]
        return v if v != -1 else None

    @property
    def flag(self) -> str:
        return self._store.flags[self._idx]

    def get_search_values(self):
        for field_name, weight in self.SEARCH_FIELDS.items():
            value = getattr(self, field_name, None)
            if value is not None:
                yield (value, weight)

    def to_dto(self) -> Country:
        return Country(
            id=self.id,
            name=self.name,
            alpha2=self.alpha2,
            alpha3=self.alpha3,
            official_name=self.official_name,
            aliases=self.aliases,
            numeric=self.numeric,
            flag=self.flag,
        )

    @classmethod
    def load(cls, filepath: Path) -> dict[int, "CountryView"]:
        store = CountryStore()
        views: dict[int, CountryView] = {}
        with open(filepath, "r", encoding="utf-8") as f:
            for id, line in enumerate(f, start=1):
                row = line.rstrip("\r\n").split("\t")
                name, alpha2, alpha3, official_name, alias_s, numeric_s, flag = row
                alias_list = [a for a in alias_s.split("|") if a]
                numeric = int(numeric_s) if numeric_s else None
                store.append(name, alpha2, alpha3, official_name, alias_list, numeric, flag)
                views[id] = cls(id, store)
        return views
