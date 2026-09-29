import csv
import logging
import time
from array import array
from localis.indexes.index import Index
from localis.utils import normalize
from collections import defaultdict

logger = logging.getLogger(__name__)


class FilterIndex(Index):
    def load(self, filepath):
        try:
            t0 = time.perf_counter()
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter="\t")
                params = next(reader)
                self.index = {p: defaultdict(lambda: array("I")) for p in params}

                row_count = 0
                for id, row in enumerate(reader, start=1):
                    row_count += 1
                    for i, cell in enumerate(row):
                        param = params[i]
                        values = cell.split("|")
                        for value in values:
                            self.index[param][value].append(id)
            logger.debug("Loaded filter index from %s: %d rows, %d params in %.3fs", filepath, row_count, len(params), time.perf_counter() - t0)
        except Exception as e:
            raise e

    def get(self, filter_kw: str, field_value: str) -> set[int]:
        if isinstance(field_value, str):
            field_value = normalize(field_value)
        ids = self.index.get(filter_kw, {}).get(field_value, set())
        return set(ids)
