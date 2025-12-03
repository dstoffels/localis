from pathlib import Path
import gzip
import pickle
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
            with gzip.open(filepath, "rb") as f:
                self.index = pickle.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load index file: {filepath}") from e
