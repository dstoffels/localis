import bisect
from array import array
from pathlib import Path
from localis.indexes.index import Index
from localis.utils import normalize


class LookupIndex(Index):
    def load(self, filepath: Path, int_filepath: Path):
        str_keys: list[str] = []
        str_vals = array("I")
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                key, id_ = line.rstrip("\n").split("\t")
                str_keys.append(key)
                str_vals.append(int(id_))

        int_keys = array("I")
        int_vals = array("I")
        with open(int_filepath, "r", encoding="utf-8") as f:
            for line in f:
                key, id_ = line.rstrip("\n").split("\t")
                int_keys.append(int(key))
                int_vals.append(int(id_))

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
