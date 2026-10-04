from typing import Any, Protocol


class CacheFilterPredicate(Protocol):
    def __call__(self, row: list[str]) -> bool: ...


def resolve_field(obj: object, field: str) -> Any:
    """The value at a dotted field path such as "country.name", or None once a step along it is None; a misspelled field raises AttributeError."""
    value: Any = obj
    for name in field.split("."):
        value = getattr(value, name)
        if value is None:
            return None
    return value
