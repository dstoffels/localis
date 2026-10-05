from array import array
from localis.entities import HistoricInfo
from .store import Store


class CountryStore(Store):
    __slots__ = (
        "alpha2s",
        "alpha3s",
        "geonames_ids",
        "official_names",
        "common_names",
        "aliases",
        "numerics",
        "flags",
        "historics",
        "macroregion_ids",
        "grouping_ids",
        "currency_ids",
        "languages",
    )

    def __init__(self):
        super().__init__()
        self.alpha2s: list[str] = []
        self.alpha3s: list[str] = []
        self.geonames_ids = array("i")  # -1 sentinel for None
        self.official_names: list[str] = []
        self.common_names: list[str] = []
        # tuples, immutable in the store; views copy them into each entity's own list
        self.aliases: list[tuple[str, ...]] = []
        self.numerics = array("i")  # -1 sentinel for None
        self.flags: list[str] = []
        self.historics: list[HistoricInfo | None] = []
        self.macroregion_ids: list[tuple[int, ...]] = []
        self.grouping_ids: list[tuple[int, ...]] = []
        self.currency_ids: list[tuple[int, ...]] = []
        # (language id, status, population_percent, script id or -1) per entry
        self.languages: list[tuple[tuple[int, str, float | None, int], ...]] = []

    def append(
        self,
        name: str,
        alpha2: str,
        alpha3: str,
        geonames_id: int | None,
        official_name: str,
        common_name: str,
        alias_list: tuple[str, ...],
        numeric: int | None,
        flag: str,
        historic: HistoricInfo | None,
        macroregion_ids: tuple[int, ...],
        grouping_ids: tuple[int, ...],
        currency_ids: tuple[int, ...],
        languages: tuple[tuple[int, str, float | None, int], ...],
    ) -> None:
        self.names.append(name)
        self.alpha2s.append(alpha2)
        self.alpha3s.append(alpha3)
        self.geonames_ids.append(geonames_id if geonames_id is not None else -1)
        self.official_names.append(official_name)
        self.common_names.append(common_name)
        self.aliases.append(alias_list)
        self.numerics.append(numeric if numeric is not None else -1)
        self.flags.append(flag)
        self.historics.append(historic)
        self.macroregion_ids.append(macroregion_ids)
        self.grouping_ids.append(grouping_ids)
        self.currency_ids.append(currency_ids)
        self.languages.append(languages)
