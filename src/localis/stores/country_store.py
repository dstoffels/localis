from array import array
from .store import Store


class CountryStore(Store):
    __slots__ = (
        "alpha2s",
        "alpha3s",
        "official_names",
        "aliases",
        "numerics",
        "flags",
    )

    def __init__(self):
        super().__init__()
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
