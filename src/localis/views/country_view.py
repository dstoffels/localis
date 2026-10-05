from pathlib import Path
from typing import Mapping, cast
from localis.entities import Country, CountryBase, CountryLanguage, CurrencyBase, HistoricInfo, LanguageStatus, MacroregionBase
from localis.stores import CountryStore
from .view import View, ViewMap
from .macroregion_view import MacroregionView
from .currency_view import CurrencyView
from .language_view import LanguageView
from .script_view import ScriptView


class CountryView(View[Country, CountryStore]):
    """Runtime view over CountryStore, used by Registry._cache; resolves its macroregions, currencies, languages and their scripts against their view mappings."""

    __slots__ = ("_macroregion_views", "_currency_views", "_language_views", "_script_views")

    def __init__(
        self,
        id: int,
        store: CountryStore,
        macroregion_views: Mapping[int, MacroregionView],
        currency_views: Mapping[int, CurrencyView],
        language_views: Mapping[int, LanguageView],
        script_views: Mapping[int, ScriptView],
    ):
        super().__init__(id, store)
        self._macroregion_views = macroregion_views
        self._currency_views = currency_views
        self._language_views = language_views
        self._script_views = script_views

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
    def official_name(self) -> str | None:
        v = self._store.official_names[self._idx]
        return v if v else None

    @property
    def common_name(self) -> str | None:
        v = self._store.common_names[self._idx]
        return v if v else None

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

    @property
    def macroregions(self) -> list[MacroregionBase]:
        return [self._macroregion_views[i].to_base() for i in self._store.macroregion_ids[self._idx]]

    @property
    def groupings(self) -> list[MacroregionBase]:
        return [self._macroregion_views[i].to_base() for i in self._store.grouping_ids[self._idx]]

    @property
    def currencies(self) -> list[CurrencyBase]:
        return [self._currency_views[i].to_base() for i in self._store.currency_ids[self._idx]]

    @property
    def languages(self) -> list[CountryLanguage]:
        entries: list[CountryLanguage] = []
        for language_id, status, percent, script_id in self._store.languages[self._idx]:
            language = self._language_views[language_id]
            entries.append(
                CountryLanguage(
                    id=language.id,
                    name=language.name,
                    alpha3=language.alpha3,
                    alpha2=language.alpha2,
                    status=cast(LanguageStatus, status),
                    population_percent=percent,
                    script=self._script_views[script_id].to_base() if script_id != -1 else None,
                )
            )
        return entries

    def to_base(self) -> CountryBase:
        return CountryBase(id=self.id, name=self.name, alpha2=self.alpha2, alpha3=self.alpha3, geonames_id=self.geonames_id)

    def to_entity(self) -> Country:
        historic = self.historic
        return Country(
            id=self.id,
            name=self.name,
            alpha2=self.alpha2,
            alpha3=self.alpha3,
            official_name=self.official_name,
            common_name=self.common_name,
            aliases=list(self.aliases),
            numeric=self.numeric,
            flag=self.flag,
            geonames_id=self.geonames_id,
            # the store's own object, so copied: a change to the entity's must not reach later calls
            historic=HistoricInfo(historic.alpha_4, historic.withdrawal_date, historic.comment) if historic else None,
            macroregions=self.macroregions,
            groupings=self.groupings,
            currencies=self.currencies,
            languages=self.languages,
        )

    @classmethod
    def load(
        cls,
        filepath: Path,
        macroregion_views: Mapping[int, MacroregionView],
        currency_views: Mapping[int, CurrencyView],
        language_views: Mapping[int, LanguageView],
        script_views: Mapping[int, ScriptView],
    ) -> ViewMap["CountryView"]:
        store = CountryStore()
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
                    common_name,
                    alias_s,
                    numeric_s,
                    flag,
                    historic_s,
                    macroregions_s,
                    groupings_s,
                    currencies_s,
                    languages_s,
                ) = row
                alias_list = tuple(a for a in alias_s.split("|") if a)
                geonames_id = int(geonames_id_s) if geonames_id_s else None
                numeric = int(numeric_s) if numeric_s else None
                historic = cls._parse_historic(historic_s)
                macroregion_ids = tuple(int(i) for i in macroregions_s.split("|") if i)
                grouping_ids = tuple(int(i) for i in groupings_s.split("|") if i)
                currency_ids = tuple(int(i) for i in currencies_s.split("|") if i)
                languages = tuple(cls._parse_language(item) for item in languages_s.split("|") if item)
                store.id_to_idx.append(idx)
                store.append(
                    name,
                    alpha2,
                    alpha3,
                    geonames_id,
                    official_name,
                    common_name,
                    alias_list,
                    numeric,
                    flag,
                    historic,
                    macroregion_ids,
                    grouping_ids,
                    currency_ids,
                    languages,
                )
                idx += 1
        return ViewMap(store, lambda id: cls(id, store, macroregion_views, currency_views, language_views, script_views))

    @staticmethod
    def _parse_language(item: str) -> tuple[int, str, float | None, int]:
        language_id, status, percent, script_id = item.split(":")
        return int(language_id), status, float(percent) if percent else None, int(script_id) if script_id else -1

    @staticmethod
    def _parse_historic(s: str) -> HistoricInfo | None:
        if not s:
            return None
        alpha_4, withdrawal_date, comment = s.split("|", 2)
        return HistoricInfo(
            alpha_4=alpha_4, withdrawal_date=withdrawal_date, comment=comment or None
        )
