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
    )

    def __init__(self):
        super().__init__()
        self.alpha2s: list[str] = []
        self.alpha3s: list[str] = []
        self.geonames_ids = array("i")  # -1 sentinel for None
        self.official_names: list[str] = []
        self.common_names: list[str] = []
        # tuples, so entities can share them without copying and callers can't mutate the cache through a returned entity
        self.aliases: list[tuple[str, ...]] = []
        self.numerics = array("i")  # -1 sentinel for None
        self.flags: list[str] = []
        self.historics: list[HistoricInfo | None] = []

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
