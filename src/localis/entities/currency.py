from dataclasses import dataclass
from .entity import Entity


@dataclass(slots=True)
class CurrencyBase(Entity):
    alpha3: str

    @property
    def key(self) -> str:
        """The stable reference to store instead of id, resolved by currencies.lookup(): the ISO 4217 alpha3."""
        return self.alpha3


@dataclass(slots=True)
class Currency(CurrencyBase):
    numeric: int | None
