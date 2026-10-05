from array import array
from .store import Store


class SubdivisionStore(Store):
    __slots__ = (
        "geonames_codes",
        "geonames_ids",
        "iso_codes",
        "types",
        "aliases",
        "admin_levels",
        "parent_ids",
        "country_ids",
    )

    def __init__(self):
        super().__init__()
        self.geonames_codes: list[str] = []
        self.geonames_ids = array("i")  # -1 sentinel for None
        self.iso_codes: list[str] = []
        self.types: list[str] = []
        # tuples, immutable in the store; views copy them into each entity's own list
        self.aliases: list[tuple[str, ...]] = []
        self.admin_levels = array("B")
        self.parent_ids = array("i")  # -1 sentinel for None
        self.country_ids = array("I")

    def append(
        self,
        name: str,
        geonames_code: str,
        geonames_id: int | None,
        iso_code: str,
        type_: str,
        alias_list: tuple[str, ...],
        admin_level: int,
        parent_id: int | None,
        country_id: int,
    ) -> None:
        self.names.append(name)
        self.geonames_codes.append(geonames_code)
        self.geonames_ids.append(geonames_id if geonames_id is not None else -1)
        self.iso_codes.append(iso_code)
        self.types.append(type_)
        self.aliases.append(alias_list)
        self.admin_levels.append(admin_level)
        self.parent_ids.append(parent_id if parent_id is not None else -1)
        self.country_ids.append(country_id)
