from dataclasses import dataclass, asdict
import json


@dataclass(slots=True)
class Entity:
    # assigned in order at each data build, so valid only within the installed version; store key instead
    id: int
    name: str

    @property
    def key(self) -> str | int:
        """The stable reference to store instead of id, resolved by the registry's lookup() in any version."""
        raise NotImplementedError

    def to_dict(self):
        return asdict(self)

    def json(self):
        return json.dumps(self.to_dict(), indent=2)

    def __str__(self):
        return self.json()
