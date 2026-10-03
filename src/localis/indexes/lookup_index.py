import bisect
from array import array
from pathlib import Path
from localis.indexes.index import Index
from localis.utils.strings import normalize
from localis.utils.data import IndexFilterPredicate


class LookupIndex(Index):
    def load(
        self,
        filepath: Path,
        int_filepath: Path,
        predicate: IndexFilterPredicate | None = None,
        allowed_ids: set[int] | None = None,
    ):
        ids = allowed_ids or set()
        # ingest doesn't write an index with no keys, so a missing file is an empty index
        str_keys: list[str] = []
        str_vals = array("I")
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    key, id_ = line.rstrip("\n").split("\t")
                    id_int = int(id_)
                    if predicate and not predicate(id_int, ids):
                        continue
                    str_keys.append(key)
                    str_vals.append(id_int)

        int_keys = array("I")
        int_vals = array("I")
        if int_filepath.exists():
            with open(int_filepath, "r", encoding="utf-8") as f:
                for line in f:
                    key, id_ = line.rstrip("\n").split("\t")
                    id_int = int(id_)
                    if predicate and not predicate(id_int, ids):
                        continue
                    int_keys.append(int(key))
                    int_vals.append(id_int)

        self._str_keys = str_keys
        self._str_vals = str_vals
        self._int_keys = int_keys
        self._int_vals = int_vals

    def get(self, key: str | int) -> int | None:
        """Get the model ID by its lookup key."""
        if isinstance(key, str):
            key = normalize(key)
            keys, vals = self._str_keys, self._str_vals
        else:
            keys, vals = self._int_keys, self._int_vals

        i = bisect.bisect_left(keys, key)
        if i < len(keys) and keys[i] == key:
            return vals[i]
        return None
