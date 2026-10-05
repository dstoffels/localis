from dataclasses import dataclass, asdict
from typing import Any, TypeVar, dataclass_transform
import json

T = TypeVar("T")


@dataclass(slots=True)
class Entity:
    """A record of a localis registry, built fresh by every call, nested records and lists included, so changing it never touches the loaded data."""

    # assigned in order at each data build, so valid only within the installed version; store key instead
    id: int
    name: str

    @property
    def key(self) -> str | int:
        """The stable reference to store instead of id, resolved by the registry's lookup() in any version."""
        raise NotImplementedError

    def __hash__(self) -> int:
        # by record rather than by every field, since list fields can't be hashed; equal entities share their type and id, so this agrees with ==
        return hash((type(self), self.id))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def __str__(self) -> str:
        return self.json()


@dataclass_transform()
def entity(cls: type[T]) -> type[T]:
    """Declares an Entity subclass as a slotted dataclass, keeping Entity's hash, which @dataclass removes from a mutable class it decorates."""
    cls = dataclass(slots=True)(cls)
    setattr(cls, "__hash__", Entity.__hash__)
    return cls
