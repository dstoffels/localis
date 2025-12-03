from localis.models import Model


class LookupIndex:
    def __init__(self, cache: dict[int, Model], lookup_fields: list[str]):
        self.cache = cache
        self.index: dict[str | int, int] = {}
        for id, model in cache.items():
            for field in lookup_fields:
                key = getattr(model, field, None)
                if isinstance(key, str):
                    key = key.lower()
                self.index[key] = id

    def get(self, key: str | int) -> Model | None:
        if isinstance(key, str):
            key = key.lower()
        model_id = self.index.get(key)

        # return None if not found, fallback to direct cache lookup by id if index miss
        return model_id and self.cache.get(model_id) or self.cache.get(key)
