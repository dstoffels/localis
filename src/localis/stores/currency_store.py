from array import array
from .store import Store


class CurrencyStore(Store):
    __slots__ = ("alpha3s", "numerics")

    def __init__(self):
        super().__init__()
        self.alpha3s: list[str] = []
        self.numerics = array("i")  # -1 sentinel for None

    def append(self, name: str, alpha3: str, numeric: int | None) -> None:
        self.names.append(name)
        self.alpha3s.append(alpha3)
        self.numerics.append(numeric if numeric is not None else -1)
