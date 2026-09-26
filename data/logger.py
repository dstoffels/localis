from pathlib import Path
from typing import Literal

BASE_PATH = Path(__file__).parent
LOG_PATH = BASE_PATH / "ingest_log.txt"


class IngestLog:
    def __init__(self, path: Path):
        self.path = path
        self._stage: Literal["COUNTRIES", "SUBDIVISIONS", "CITIES", ""] = ""

    def set_stage(self, stage: Literal["COUNTRIES", "SUBDIVISIONS", "CITIES"]) -> None:
        self._stage = stage

    def writeline(self, message: str) -> None:
        line = f"[{self._stage}] {message}"
        # print(line)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def clear(self) -> None:
        self.path.write_text("", encoding="utf-8")


log = IngestLog(LOG_PATH)
