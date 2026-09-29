from array import array
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Index:
    def __init__(
        self,
        filepath: Path,
        **kwargs,
    ):
        self.index: dict[str, int | array] = {}
        self.load(filepath, **kwargs)

    def load(self, filepath: Path, **kwargs):
        pass
