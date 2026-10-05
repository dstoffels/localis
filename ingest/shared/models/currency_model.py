from dataclasses import dataclass
from .model import Model


@dataclass(slots=True)
class CurrencyModel(Model):
    """An ISO 4217 currency or fund code."""

    alpha3: str
    numeric: int | None

    LOOKUP_FIELDS = ("alpha3", "numeric")
    FILTER_FIELDS = {"name": ("name",)}
    CANON_FIELDS = ("name",)
    SHORT_NAMES = True
