from dataclasses import dataclass, asdict
import json


@dataclass(slots=True)
class Entity:
    id: int
    name: str

    def to_dict(self):
        return asdict(self)

    def json(self):
        return json.dumps(self.to_dict(), indent=2)

    def __str__(self):
        return self.json()
