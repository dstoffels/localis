import csv
from array import array
from pathlib import Path
from localis.indexes.index import Index
from localis.utils.strings import normalize
from localis.utils.data import IndexFilterPredicate


class FilterIndex(Index):
    def load(
        self,
        filepath: Path,
        predicate: IndexFilterPredicate | None = None,
        allowed_ids: set[int] | None = None,
    ):
        ids = allowed_ids or set()
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            params = next(reader)
            # during the load a value's postings are its lone id, or a list once a second record shares it
            index: dict[str, dict[str, int | list[int]]] = {p: {} for p in params}

            for id, row in enumerate(reader, start=1):
                if predicate and not predicate(id, ids):
                    continue
                for i, cell in enumerate(row):
                    postings = index[params[i]]
                    for value in cell.split("|"):
                        existing = postings.get(value)
                        if existing is None:
                            postings[value] = id
                        elif isinstance(existing, int):
                            postings[value] = [existing, id]
                        else:
                            existing.append(id)

        # most values belong to a single record, whose id is kept as a plain int rather than a whole array; the rest are packed at their exact size
        self.index: dict[str, dict[str, int | array]] = {}
        for param in params:
            # popped so each parameter's load-time postings are freed as soon as they're converted
            postings = index.pop(param)
            self.index[param] = {
                value: value_ids if isinstance(value_ids, int) else array("I", value_ids)
                for value, value_ids in postings.items()
            }

    def get(self, filter_kw: str, field_value: str | int) -> set[int]:
        # every indexed cell is stored as a string, so a scalar like admin_level=1 is stringified before lookup
        ids = self.index.get(filter_kw, {}).get(normalize(str(field_value)))
        if ids is None:
            return set()
        return {ids} if isinstance(ids, int) else set(ids)
