import logging
from pathlib import Path
from localis.models import Model

logger = logging.getLogger(__name__)


class Index:
    def __init__(
        self,
        model_cls: type[Model],
        cache: dict[int, Model],
        filepath: Path,
        **kwargs,
    ):
        self.MODEL_CLS = model_cls
        self.cache = cache
        self.index: dict[str, int | list[int]] = {}
        self.load(filepath)

    def load(self, filepath: Path):
        pass
