from pathlib import Path
from localis.entities import Currency, CurrencyBase
from localis.stores import CurrencyStore
from .view import View, ViewMap


class CurrencyView(View[Currency, CurrencyStore]):
    """Runtime view over CurrencyStore, used by Registry._cache."""

    __slots__ = ()

    @property
    def name(self) -> str:
        return self._store.names[self._idx]

    @property
    def alpha3(self) -> str:
        return self._store.alpha3s[self._idx]

    @property
    def numeric(self) -> int | None:
        v = self._store.numerics[self._idx]
        return v if v != -1 else None

    def to_base(self) -> CurrencyBase:
        return CurrencyBase(id=self.id, name=self.name, alpha3=self.alpha3)

    def to_entity(self) -> Currency:
        return Currency(id=self.id, name=self.name, alpha3=self.alpha3, numeric=self.numeric)

    @classmethod
    def load(cls, filepath: Path) -> ViewMap["CurrencyView"]:
        store = CurrencyStore()
        with open(filepath, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                name, alpha3, numeric_s = line.rstrip("\r\n").split("\t")
                store.id_to_idx.append(idx)
                store.append(name, alpha3, int(numeric_s) if numeric_s else None)
        return ViewMap(store, lambda id: cls(id, store))
