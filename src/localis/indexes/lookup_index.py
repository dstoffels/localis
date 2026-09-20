import logging
import time
from localis.indexes.index import Index
from localis.utils import normalize

logger = logging.getLogger(__name__)


class LookupIndex(Index):
    def load(self, filepath):
        try:
            t0 = time.perf_counter()
            with open(filepath, "r", encoding="utf-8") as f:
                for id, line in enumerate(f, start=1):
                    keys: list[str] = line.strip().split("|")
                    for key in keys:
                        if key.isdigit():
                            key = int(key)
                        self.index[key] = id
            logger.debug("Loaded lookup index from %s: %d entries in %.3fs", filepath, len(self.index), time.perf_counter() - t0)
        except Exception as e:
            raise Exception(f"Failed to load lookup index from {filepath}: {e}")

    def get(self, key: str | int) -> int | None:
        """Get the model ID by its lookup key."""
        if isinstance(key, str):
            key = normalize(key)

        # try to get the model ID from the index
        return self.index.get(key)
