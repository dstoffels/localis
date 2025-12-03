from localis.models import Model
from localis.indexes.index import Index
from localis.utils import normalize, ModelData


class LookupIndex(Index):
    def get(self, key: str | int) -> int | None:
        """Get the model ID by its lookup key."""
        if isinstance(key, str):
            key = normalize(key)

        # try to get the model ID from the index
        model_id: int = self.index.get(key)

        # return the model instance if found
        return model_id
