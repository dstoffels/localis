from pathlib import Path
import gzip
import json
from localis.models import Model
import pickle


class Index:
    def __init__(
        self,
        model_cls: Model,
        cache: dict[int, list[str | int | list[str]]],
        filepath: Path,
        **kwargs,
    ):
        self.MODEL_CLS = model_cls
        self.cache = cache
        self.index: dict[str, int | list[int]] = None

        try:
            bytes = gzip.open(filepath, "rb").read()
            self.index = json.loads(bytes.decode("utf-8"))
        except Exception as e:
            raise RuntimeError(f"Failed to load index file: {filepath}") from e
