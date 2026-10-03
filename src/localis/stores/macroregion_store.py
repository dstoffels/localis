from array import array
from .store import Store


class MacroregionStore(Store):
    __slots__ = ("codes", "types", "parent_ids")

    def __init__(self):
        super().__init__()
        self.codes: list[str] = []
        self.types: list[str] = []
        self.parent_ids = array("i")  # -1 sentinel for None

    def append(self, name: str, code: str, type_: str, parent_id: int | None) -> None:
        self.names.append(name)
        self.codes.append(code)
        self.types.append(type_)
        self.parent_ids.append(parent_id if parent_id is not None else -1)
