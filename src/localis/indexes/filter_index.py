from localis.models import Model
from localis.indexes.index import Index
from localis.utils import normalize
import csv
from collections import defaultdict


class FilterIndex(Index):
    def __init__(self, model_cls, cache, filepath, **kwargs):
        self.index: dict[str, dict[str, set[int]]] = defaultdict(
            lambda: defaultdict(set)
        )
        super().__init__(model_cls, cache, filepath, **kwargs)

    def load(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter="\t")
                params = next(reader)
                self.index = {p: defaultdict(set) for p in params}

                for id, row in enumerate(reader, start=1):
                    for i, cell in enumerate(row):
                        param = params[i]
                        values = cell.split("|")
                        for value in values:
                            self.index[param][value].add(id)
        except Exception as e:
            raise e

    def filter(self, filter_kw: str, field_value: str) -> set[int]:
        if isinstance(field_value, str):
            field_value = normalize(field_value)
        ids = self.index.get(filter_kw, {}).get(field_value, set())
        return set(ids)
