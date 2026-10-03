from pathlib import Path
from typing import Literal

BASE_PATH = Path(__file__).parent.parent

Stage = Literal["MACROREGIONS", "COUNTRIES", "SUBDIVISIONS", "CITIES"]
Level = Literal["INFO", "WARN"]

STAGE_FILES: dict[Stage, Path] = {
    "MACROREGIONS": BASE_PATH / "macroregions" / "logs" / "macroregions_ingest.log",
    "COUNTRIES": BASE_PATH / "countries" / "logs" / "countries_ingest.log",
    "SUBDIVISIONS": BASE_PATH / "subdivisions" / "logs" / "subdivisions_ingest.log",
    "CITIES": BASE_PATH / "cities" / "logs" / "cities_ingest.log",
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
        """Write this stage's buffered lines to its own file, replacing whatever that file held from the previous run."""
        if self._stage is None:
            return
        path = STAGE_FILES[self._stage]
        path.parent.mkdir(parents=True, exist_ok=True)
        text = f"[{self._stage}]\n"
        text += "\n".join(self._lines)
        path.write_text(text + "\n" if text else "", encoding="utf-8")


ingest_log = IngestLog()
