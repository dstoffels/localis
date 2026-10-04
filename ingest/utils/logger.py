from pathlib import Path
from typing import Literal
from .paths import MACROREGIONS_LOGS_PATH, CURRENCIES_LOGS_PATH, SCRIPTS_LOGS_PATH, COUNTRIES_LOGS_PATH, SUBDIVISIONS_LOGS_PATH, CITIES_LOGS_PATH

Stage = Literal["MACROREGIONS", "CURRENCIES", "SCRIPTS", "COUNTRIES", "SUBDIVISIONS", "CITIES"]
Level = Literal["INFO", "WARN"]

STAGE_FILES: dict[Stage, Path] = {
    "MACROREGIONS": MACROREGIONS_LOGS_PATH / "macroregions_ingest.log",
    "CURRENCIES": CURRENCIES_LOGS_PATH / "currencies_ingest.log",
    "SCRIPTS": SCRIPTS_LOGS_PATH / "scripts_ingest.log",
    "COUNTRIES": COUNTRIES_LOGS_PATH / "countries_ingest.log",
    "SUBDIVISIONS": SUBDIVISIONS_LOGS_PATH / "subdivisions_ingest.log",
    "CITIES": CITIES_LOGS_PATH / "cities_ingest.log",
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
