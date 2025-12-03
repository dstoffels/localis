from localis.models import Model
from localis.indexes.index import Index
from localis.utils import normalize, ModelData


class LookupIndex(Index):
    # def __init__(self, cache: dict[int, Model], lookup_fields: list[str]):
    #     self.cache = cache
    #     self.index: dict[str | int, int] = {}
    #     for id, model in cache.items():
    #         for field in lookup_fields:
    #             key = getattr(model, field, None)
    #             if isinstance(key, str):
    #                 key = key.lower()
    #             self.index[key] = id

    def get(self, key: str | int) -> Model | None:
        """Get the model ID by its lookup key."""
        if isinstance(key, str):
            key = normalize(key)

        # try to get the model ID from the index
        model_id: int = self.index.get(key)

        # fetch the model data (list) from the cache, use key if no model_id
        model_data: ModelData | None = self.cache.get(model_id or key)

        # return the model instance if found
        return model_data and self.MODEL_CLS(*model_data)
