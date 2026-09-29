from abc import ABC, abstractmethod


class Store(ABC):
    """Columnar storage backing each View; one instance per registry, indexed by (id - 1)."""

    __slots__ = ("names",)

    def __init__(self):
        self.names: list[str] = []

    @abstractmethod
    def append(self, *args, **kwargs) -> None: ...

    def __len__(self) -> int:
        return len(self.names)
