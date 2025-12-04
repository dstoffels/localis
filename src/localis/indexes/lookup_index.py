from localis.models import Model
from localis.indexes.index import Index
from localis.utils import normalize, ModelData
import csv


class LookupIndex(Index):
    def load(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for id, line in enumerate(f, start=1):
                    keys: list[str] = line.strip().split("|")
                    for key in keys:
                        if key.isdigit():
                            key = int(key)
                        self.index[key] = id
        except Exception as e:
            raise Exception(f"Failed to load lookup index from {filepath}: {e}")

    def get(self, key: str | int) -> int | None:
        """Get the model ID by its lookup key."""
        if isinstance(key, str):
            key = normalize(key)

        # try to get the model ID from the index
        return self.index.get(key)
