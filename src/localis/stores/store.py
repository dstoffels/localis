from abc import ABC, abstractmethod


class Store(ABC):
    """Columnar storage shared by every entity's View. One instance per registry,
    holding every record's fields as parallel arrays/lists appended to during
    load, indexed by (id - 1)."""

    __slots__ = ("names",)

    def __init__(self):
        self.names: list[str] = []

    @abstractmethod
    def append(self, *args, **kwargs) -> None: ...

    def __len__(self) -> int:
        return len(self.names)
