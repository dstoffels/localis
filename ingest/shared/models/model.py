from dataclasses import dataclass, asdict
import json
from collections import defaultdict
from typing import ClassVar
from localis.utils.strings import generate_trigrams, normalize


@dataclass(slots=True)
class Model:
    """Ingestion-only representation: carries the field-processing API (row
    serialization, lookup/filter/search extraction) used to build the on-disk
    data files consumed at runtime by localis's Store/View classes. Deliberately
    independent of DTO, the runtime return type, no shared base class."""

    id: int
    name: str

    def to_dict(self):
        return asdict(self)

    def json(self):
        return json.dumps(self.to_dict(), indent=2)

    def __str__(self):
        return self.json()

    # ----------- Serialization Methods ----------- #
    def to_row(self) -> tuple[str | int | None]:
        return tuple(self.to_dict().values())

    # ----------- Indexing Methods ----------- #

    LOOKUP_FIELDS: ClassVar[tuple[str, ...]] = ()
    # all-digit lookup values go to the integer lookup index; False keeps them as strings (codes with leading zeros, like M49's "009")
    NUMERIC_LOOKUP: ClassVar[bool] = True

    def extract_lookup_values(self):
        """Used in processing to produce a normalized lookup index for each model from its LOOKUP_FIELDS."""

        for field in self.LOOKUP_FIELDS:
            value: str = getattr(self, field)
            if value:
                yield normalize(value)

    FILTER_FIELDS: ClassVar[dict[str, tuple[str, ...]]] = defaultdict(tuple)
    """Fields that can be used for filtering. Key is the filter name, value is a tuple of field names to search on."""

    def extract_filter_values(self) -> dict[str, list[str]]:
        """Used in processing to produce a normalized filter index for each model from its FILTER_FIELDS."""
        filter_values: dict[str, set[str]] = {}

        for param, field_names in self.FILTER_FIELDS.items():
            filter_values[param] = set()
            for field in field_names:
                obj = self
                value: str | list[str] | None = None
                for nested in field.split("."):
                    value = getattr(obj, nested)
                    if value is None:
                        break
                    obj = value

                if isinstance(value, list):
                    for v in value:
                        filter_values[param].add(normalize(v))

                elif value is not None:
                    filter_values[param].add(normalize(value))

        return {
            filter_name: sorted(values, key=str)
            for filter_name, values in filter_values.items()
        }

    SEARCH_FIELDS: ClassVar[dict[str, float]] = {}
    """Fields that are used to identify the obj when searching. Key is the field name (can be nested fields using dot notation), value is the weight for search relevance."""

    def extract_search_trigrams(self):
        """Used in processing to produce a normalized, trigram search index for each model from its SEARCH_FIELDS keys."""
        values = []

        for field in self.SEARCH_FIELDS.keys():
            obj = self
            value: str | list[str] | None = None
            for nested in field.split("."):
                value = getattr(obj, nested, None)
                if value is None:
                    break
                obj = value

            if isinstance(value, list):
                for v in value:
                    values.append(v)

            elif value is not None:
                values.append(value)

        return generate_trigrams(normalize(" ".join(values)))
