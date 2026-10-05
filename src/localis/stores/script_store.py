from array import array
from .store import Store


class ScriptStore(Store):
    __slots__ = ("alpha4s", "numerics", "aliases")

    def __init__(self):
        super().__init__()
        self.alpha4s: list[str] = []
        self.numerics = array("i")  # -1 sentinel for None
        # tuples, immutable in the store; views copy them into each entity's own list
        self.aliases: list[tuple[str, ...]] = []

    def append(self, name: str, alpha4: str, numeric: int | None, alias_list: tuple[str, ...]) -> None:
        self.names.append(name)
        self.alpha4s.append(alpha4)
        self.numerics.append(numeric if numeric is not None else -1)
        self.aliases.append(alias_list)
