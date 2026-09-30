from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

BASE_PATH = Path(__file__).parent.parent

Stage = Literal["COUNTRIES", "SUBDIVISIONS", "CITIES"]
Level = Literal["INFO", "WARN"]

STAGE_FILES: dict[Stage, Path] = {
    "COUNTRIES": BASE_PATH / "countries" / "logs" / "countries_ingest_log.txt",
    "SUBDIVISIONS": BASE_PATH / "subdivisions" / "logs" / "subdivisions_ingest_log.txt",
    "CITIES": BASE_PATH / "cities" / "logs" / "cities_ingest_log.txt",
}


class IngestLog:
    def __init__(self):
        self._stage: Stage | None = None
        self._lines: list[str] = []

    def set_stage(self, stage: Stage) -> None:
        self._stage = stage
        self._lines = []

    def writeline(self, message: str, level: Level = "INFO") -> None:
        line = f"[{level}] {message}"
        print(line)
        self._lines.append(line)

    def dump(self) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        """Write this stage's buffered lines to its own file, replacing whatever that file held from the previous run."""
        if self._stage is None:
            return
        path = STAGE_FILES[self._stage]
        text = f"[{self._stage}] {timestamp}\n"
        text += "\n".join(self._lines)
        path.write_text(text + "\n" if text else "", encoding="utf-8")


ingest_log = IngestLog()
