import csv
from array import array
from pathlib import Path
from localis.indexes.index import Index
from localis.utils.strings import normalize
from collections import defaultdict
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
            index: dict[str, dict[str, array]] = {
                p: defaultdict(lambda: array("I")) for p in params
            }

            for id, row in enumerate(reader, start=1):
                if predicate and not predicate(id, ids):
                    continue
                for i, cell in enumerate(row):
                    param = params[i]
                    values = cell.split("|")
                    for value in values:
                        index[param][value].append(id)

            self.index = index

    def get(self, filter_kw: str, field_value: str | int) -> set[int]:
        # every indexed cell is stored as a string, so a scalar like admin_level=1 is stringified before lookup
        ids = self.index.get(filter_kw, {}).get(normalize(str(field_value)), set())
        return set(ids)
