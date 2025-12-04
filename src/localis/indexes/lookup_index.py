from localis.models import Model
from localis.indexes.index import Index
from localis.utils import normalize, ModelData
import csv


class LookupIndex(Index):
    def load(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter="\t")
                last_id = 0
                for id, key in reader:
                    if id and id != last_id:
                        last_id = int(id)
                    self.index[key] = last_id
        except Exception as e:
            raise Exception(f"Failed to load lookup index from {filepath}: {e}")

    def get(self, key: str | int) -> int | None:
        """Get the model ID by its lookup key."""
        if isinstance(key, str):
            key = normalize(key)

        # try to get the model ID from the index
        model_id: int = self.index.get(key)

        # return the model instance if found
        return model_id
