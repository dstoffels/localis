from dataclasses import dataclass, asdict, fields
import json
from collections import defaultdict


def extract_base(from_obj, depth=1):
    """Returns an instance of a base class populated with subclass obj data. Can select from multiple base classes by index."""
    target_cls = from_obj.__class__.__mro__[depth]
    field_names = {f.name for f in fields(target_cls)}
    data = {slot: getattr(from_obj, slot) for slot in field_names}
    return target_cls(**data)


@dataclass(slots=True)
class DTO:
    id: int
    name: str

    def to_dict(self):
        return asdict(self)

    def json(self):
        return json.dumps(self.to_dict(), indent=2)

    def __str__(self):
        return self.json()


# @dataclass(slots=True)
class Model(DTO):
    search_tokens: str
    search_fields: tuple[str] = ()
    search_context: str = ""

    @property
    def dto(self) -> DTO:
        return extract_base(self)

    def set_search_meta(self):
        pass
