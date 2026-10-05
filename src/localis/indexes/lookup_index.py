import bisect
from array import array
from pathlib import Path
from typing import Sequence, TypeVar
from localis.utils.strings import normalize

K = TypeVar("K", str, int)


class LookupIndex:
    """A registry's lookup keys, string and integer, each sorted for binary search, mapped to record ids."""

    def __init__(
        self,
        filepath: Path,
        int_filepath: Path,
        allowed_ids: set[int] | None = None,
    ) -> None:
        # ingest doesn't write an index with no keys, so a missing file is an empty index
        str_keys: list[str] = []
        str_vals = array("I")
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    key, id_ = line.rstrip("\n").split("\t")
                    id_int = int(id_)
                    if allowed_ids is not None and id_int not in allowed_ids:
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
                    if allowed_ids is not None and id_int not in allowed_ids:
                        continue
                    int_keys.append(int(key))
                    int_vals.append(id_int)

        self._str_keys = str_keys
        self._str_vals = str_vals
        self._int_keys = int_keys
        self._int_vals = int_vals

    def get(self, key: str | int) -> int | None:
        """The record id a lookup key resolves to, or None; raises TypeError for a key that isn't a str or an int."""
        if isinstance(key, bool) or not isinstance(key, (str, int)):
            raise TypeError(f"lookup key must be a str or an int, got {key!r}")
        if isinstance(key, int):
            return self._find(self._int_keys, self._int_vals, key)
        key = normalize(key)
        found = self._find(self._str_keys, self._str_vals, key)
        # an all-digit code (a numeric code, a GeoNames id) is indexed as an integer, so "840" also tries 840
        if found is None and key.isdigit():
            found = self._find(self._int_keys, self._int_vals, int(key))
        return found

    @staticmethod
    def _find(keys: Sequence[K], vals: array, key: K) -> int | None:
        i = bisect.bisect_left(keys, key)
        if i < len(keys) and keys[i] == key:
            return vals[i]
        return None
