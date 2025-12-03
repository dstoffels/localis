from localis.models import Model
from localis.indexes.index import Index
from localis.utils import normalize


class FilterIndex(Index):
    def __init__(self, model_cls, cache, filepath, **kwargs):
        self.index: dict[str, dict[str, set[int]]] = {}
        super().__init__(model_cls, cache, filepath, **kwargs)

    def filter(self, filter_kw: str, field_value: str) -> set[int]:
        if isinstance(field_value, str):
            field_value = normalize(field_value)
        ids = self.index.get(filter_kw, {}).get(field_value, set())
        return set(ids)
