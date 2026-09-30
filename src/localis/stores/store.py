from abc import ABC, abstractmethod
from array import array


class Store(ABC):
    """Columnar storage backing each View; `id_to_idx[id - 1]` gives a row's physical position, or -1 if that id was excluded by a load-time filter predicate."""

    __slots__ = ("names", "id_to_idx")

    def __init__(self):
        self.names: list[str] = []
        self.id_to_idx: array = array("i")

    @abstractmethod
    def append(self, *args, **kwargs) -> None: ...

    def __len__(self) -> int:
        return len(self.names)
