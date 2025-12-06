from pathlib import Path
from localis.models import Model


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
        self.index: dict[str, int | list[int]] = {}
        self.load(filepath)

    def load(self, filepath: Path):
        pass
