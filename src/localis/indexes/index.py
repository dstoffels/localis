from array import array
from pathlib import Path


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
