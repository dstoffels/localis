from .entity import Entity, entity


@entity
class CurrencyBase(Entity):
    """A currency as other records nest it."""

    alpha3: str

    @property
    def key(self) -> str:
        """The stable reference to store instead of id, resolved by currencies.lookup(): the ISO 4217 alpha3."""
        return self.alpha3


@entity
class Currency(CurrencyBase):
    """An ISO 4217 currency or fund code."""

    numeric: int | None
