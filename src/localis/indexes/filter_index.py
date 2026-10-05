from array import array
from enum import Enum
from pathlib import Path
from typing import Final, Literal
from localis.utils.strings import normalize
from .inverted_index import read_inverted_index, keep_allowed


class _MissingType(Enum):
    MISSING = "MISSING"

    def __repr__(self) -> str:
        return "MISSING"


# a filter value matching the records with no value in that field, since None means "don't filter on this field"
MISSING: Final = _MissingType.MISSING
Missing = Literal[_MissingType.MISSING]
# the key those records are indexed under; uppercase, so no normalized query value can equal it
MISSING_KEY = "MISSING"


class FilterIndex:
    def __init__(
        self,
        prefix: Path,
        allowed_ids: set[int] | None = None,
    ) -> None:
        postings, rows = read_inverted_index(prefix)
        # most values belong to a single record, whose id is kept as a plain int rather than a whole array; the rest are sliced at their exact size
        self.index: dict[str, dict[str, int | array]] = {}
        for (field, value), offset, count in rows:
            # rows are sorted by field, so a field's dict is created once, even if none of its values survive allowed_ids
            values = self.index.get(field)
            if values is None:
                values = self.index[field] = {}
            if count == 1:
                id = postings[offset]
                if allowed_ids is None or id in allowed_ids:
                    values[value] = id
                continue
            ids = keep_allowed(postings[offset : offset + count], allowed_ids)
            if len(ids) > 1:
                values[value] = ids
            elif ids:
                values[value] = ids[0]

    def get(self, filter_kw: str, field_value: str | int | Missing) -> set[int]:
        # every indexed value is stored as a string, so a scalar like admin_level=1 is stringified before lookup
        key = MISSING_KEY if field_value is MISSING else normalize(str(field_value))
        ids = self.index.get(filter_kw, {}).get(key)
        if ids is None:
            return set()
        return {ids} if isinstance(ids, int) else set(ids)
