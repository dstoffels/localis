from contextlib import contextmanager
from typing import Iterator, Literal
from .paths import Stage

Level = Literal["INFO", "WARN", "ERROR"]


class IngestLog:
    def __init__(self):
        self._stage: Stage | None = None
        self._lines: list[str] = []

    @contextmanager
    def stage(self, stage: Stage) -> Iterator[None]:
        """Logs a stage to its own file, replacing the previous run's, written even when the stage fails; an exception that stops it is logged as an ERROR line before it propagates."""
        self._stage = stage
        self._lines = []
        try:
            yield
        except Exception as e:
            self.writeline(f"{type(e).__name__}: {e}", level="ERROR")
            raise
        finally:
            self.dump()

    def writeline(self, message: str, level: Level = "INFO") -> None:
        line = f"[{level}] {message}"
        print(line)
        self._lines.append(line)

    def dump(self) -> None:
        """Write this stage's buffered lines to its own file, replacing whatever that file held from the previous run."""
        if self._stage is None:
            return
        path = self._stage.log_file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join([f"[{self._stage.name.upper()}]", *self._lines]) + "\n", encoding="utf-8")


ingest_log = IngestLog()
