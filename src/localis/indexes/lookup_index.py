import bisect
from array import array
from pathlib import Path
from typing import Sequence, TypeVar
from localis.utils.strings import normalize
from localis.utils.data import open_data

K = TypeVar("K", str, int)


class LookupIndex:
    """A registry's lookup keys, string and integer, each sorted for binary search, mapped to record ids."""

    def __init__(
        self,
        filepath: Path,
        int_filepath: Path,
        allowed_ids: set[int] | None = None,
    ) -> None:
        self._str_keys, self._str_vals = self._read(filepath, allowed_ids)
        int_keys, self._int_vals = self._read(int_filepath, allowed_ids)
        self._int_keys = array("I", map(int, int_keys))

    @staticmethod
    def _read(path: Path, allowed_ids: set[int] | None) -> tuple[list[str], array]:
        keys: list[str] = []
        ids = array("I")
        # ingest writes no file for an index with no keys
        if not path.exists():
            return keys, ids
        with open_data(path) as f:
            for line in f:
                key, id_s = line.rstrip("\n").split("\t")
                record_id = int(id_s)
                if allowed_ids is None or record_id in allowed_ids:
                    keys.append(key)
                    ids.append(record_id)
        return keys, ids

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
