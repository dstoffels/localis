from pathlib import Path


class Index:
    def __init__(
        self,
        filepath: Path,
        **kwargs,
    ):
        self.load(filepath, **kwargs)

    def load(self, *args, **kwargs) -> None:
        pass
