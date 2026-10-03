from pathlib import Path
from localis.entities import Country, HistoricInfo
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
    def geonames_id(self) -> int | None:
        v = self._store.geonames_ids[self._idx]
        return v if v != -1 else None

    @property
    def official_name(self) -> str:
        return self._store.official_names[self._idx]

    @property
    def aliases(self) -> tuple[str, ...]:
        return self._store.aliases[self._idx]

    @property
    def numeric(self) -> int | None:
        v = self._store.numerics[self._idx]
        return v if v != -1 else None

    @property
    def flag(self) -> str | None:
        v = self._store.flags[self._idx]
        return v if v else None

    @property
    def historic(self) -> HistoricInfo | None:
        return self._store.historics[self._idx]

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
            geonames_id=self.geonames_id,
            historic=self.historic,
        )

    @classmethod
    def load(cls, filepath: Path) -> dict[int, "CountryView"]:
        store = CountryStore()
        views: dict[int, CountryView] = {}
        idx = 0
        with open(filepath, "r", encoding="utf-8") as f:
            for id, line in enumerate(f, start=1):
                row = line.rstrip("\r\n").split("\t")
                (
                    name,
                    alpha2,
                    alpha3,
                    geonames_id_s,
                    official_name,
                    alias_s,
                    numeric_s,
                    flag,
                    historic_s,
                ) = row
                alias_list = tuple(a for a in alias_s.split("|") if a)
                geonames_id = int(geonames_id_s) if geonames_id_s else None
                numeric = int(numeric_s) if numeric_s else None
                historic = cls._parse_historic(historic_s)
                store.id_to_idx.append(idx)
                store.append(
                    name,
                    alpha2,
                    alpha3,
                    geonames_id,
                    official_name,
                    alias_list,
                    numeric,
                    flag,
                    historic,
                )
                views[id] = cls(id, store)
                idx += 1
        return views

    @staticmethod
    def _parse_historic(s: str) -> HistoricInfo | None:
        if not s:
            return None
        alpha_4, withdrawal_date, comment = s.split("|", 2)
        return HistoricInfo(
            alpha_4=alpha_4, withdrawal_date=withdrawal_date, comment=comment or None
        )
