from dataclasses import dataclass, asdict, fields
import json
from collections import defaultdict
from localis.utils import generate_trigrams, normalize


def extract_base(from_obj, depth=1):
    """Returns an instance of a base class populated with subclass obj data. Depth indicates how many levels up the MRO to go."""
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


class Model(DTO):
    # ----------- Serialization Methods ----------- #
    def to_dto(self) -> DTO:
        return extract_base(self)

    def to_row(self) -> tuple[str | int | None]:
        return tuple(self.to_dict().values())

    @classmethod
    def from_row(cls, id: int, row: list[str | int | None], **kwargs) -> "Model":
        return cls(id, *row)

    # ----------- Indexing Methods ----------- #

    LOOKUP_FIELDS: tuple[str] = ()

    def extract_lookup_values(self):
        """Used in processing to produce a normalized lookup index for each model from its LOOKUP_FIELDS."""

        for field in self.LOOKUP_FIELDS:
            value: str = getattr(self, field)
            if value:
                yield normalize(value)

    FILTER_FIELDS: dict[str, tuple[str]] = defaultdict(tuple)
    """Fields that can be used for filtering. Key is the filter name, value is a tuple of field names to search on."""

    def extract_filter_values(self) -> dict[str, set[str]]:
        """Used in processing to produce a normalized filter index for each model from its FILTER_FIELDS."""
        filter_values: dict[str, set[str]] = {}

        for param, field_names in self.FILTER_FIELDS.items():
            filter_values[param] = set()
            for field in field_names:
                obj = self
                for nested in field.split("."):
                    value: str | list[str] = getattr(obj, nested)
                    if value is None:
                        break
                    obj = value

                if isinstance(value, list):
                    for v in value:
                        filter_values[param].add(normalize(v))

                elif value is not None:
                    filter_values[param].add(normalize(value))

        return filter_values

    SEARCH_FIELDS: dict[str, float] = {}
    """Fields that are used to identify the obj when searching. Key is the field name (can be nested fields using dot notation), value is the weight for search relevance."""

    def extract_search_trigrams(self):
        """Used in processing to produce a normalized, trigram search index for each model from its SEARCH_FIELDS keys."""
        values = []

        for field in self.SEARCH_FIELDS.keys():
            obj = self
            for nested in field.split("."):
                value: str | list[str] = getattr(obj, nested, None)
                if value is None:
                    break
                obj = value

            if isinstance(value, list):
                for v in value:
                    values.append(v)

            elif value is not None:
                values.append(value)

        return generate_trigrams(normalize(" ".join(values)))

    def get_search_values(self):
        for field_name, weight in self.SEARCH_FIELDS.items():
            obj = self
            for nested in field_name.split("."):
                value: str | list[str] = getattr(obj, nested, None)
                if value is None:
                    break
                obj = value

            if value is not None:
                yield (value, weight)
