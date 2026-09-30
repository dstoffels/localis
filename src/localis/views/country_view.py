from pathlib import Path
from localis.entities import Country
from localis.stores import CountryStore
from .view import View


class CountryView(View[Country, CountryStore]):
    """Runtime view over CountryStore, used by Registry._cache."""

    __slots__ = ()

    @property
    def name(self) -> str:
        return self._store.names[self._idx]

    @property
    def alpha2(self) -> str:
        return self._store.alpha2s[self._idx]

    @property
    def alpha3(self) -> str | None:
        v = self._store.alpha3s[self._idx]
        return v if v else None

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
    def flag(self) -> str | None:
        v = self._store.flags[self._idx]
        return v if v else None

    def to_entity(self) -> Country:
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
                store.id_to_idx.append(len(store))
                store.append(
                    name, alpha2, alpha3, official_name, alias_list, numeric, flag
                )
                views[id] = cls(id, store)
        return views
