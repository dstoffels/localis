from localis.models import Model
from collections import defaultdict


class FilterIndex:
    def __init__(self, cache: dict[int, Model], filter_fields: dict[str, tuple[str]]):
        self.cache = cache
        self.index: dict[str, dict[str, set[int]]] = defaultdict(
            lambda: defaultdict(set)
        )

        for id, model in cache.items():
            for kwarg_key, field_names in filter_fields.items():
                for field in field_names:
                    obj = model
                    for nested in field.split("."):
                        key = getattr(obj, nested, None)
                        if key is None:
                            break
                        obj = key

                    if isinstance(key, list):
                        for item in key:
                            if item:
                                self.index[kwarg_key][item.lower()].add(id)
                    elif isinstance(key, str):
                        key = key.lower()
                        if key:
                            self.index[kwarg_key][key].add(id)

    def get(self, kwarg_key: str, field_value: str) -> set[Model]:
        if isinstance(field_value, str):
            field_value = field_value.lower()
        id = self.index.get(kwarg_key.lower(), {}).get(field_value, set())
        return id
