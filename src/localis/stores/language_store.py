from .store import Store


class LanguageStore(Store):
    __slots__ = ("alpha3s", "alpha2s", "bibliographics", "scopes", "types", "inverted_names", "aliases", "script_ids", "secondary_script_ids")

    def __init__(self):
        super().__init__()
        self.alpha3s: list[str] = []
        self.alpha2s: list[str] = []
        self.bibliographics: list[str] = []
        self.scopes: list[str] = []
        self.types: list[str] = []
        self.inverted_names: list[str] = []
        self.aliases: list[tuple[str, ...]] = []
        self.script_ids: list[tuple[int, ...]] = []
        self.secondary_script_ids: list[tuple[int, ...]] = []

    def append(
        self,
        name: str,
        alpha3: str,
        alpha2: str,
        bibliographic: str,
        scope: str,
        type_: str,
        inverted_name: str,
        alias_list: tuple[str, ...],
        script_ids: tuple[int, ...],
        secondary_script_ids: tuple[int, ...],
    ) -> None:
        self.names.append(name)
        self.alpha3s.append(alpha3)
        self.alpha2s.append(alpha2)
        self.bibliographics.append(bibliographic)
        self.scopes.append(scope)
        self.types.append(type_)
        self.inverted_names.append(inverted_name)
        self.aliases.append(alias_list)
        self.script_ids.append(script_ids)
        self.secondary_script_ids.append(secondary_script_ids)
