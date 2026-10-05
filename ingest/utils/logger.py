from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Literal
from .paths import Stage, PIPELINE_LOG_PATH

Level = Literal["INFO", "WARN", "ERROR"]

# a run stopped by subdivision orphans, which CI tells apart from a failure
ORPHANS_EXIT_CODE = 10


def _line(message: str, level: Level) -> str:
    line = f"[{level}] {message}"
    print(line)
    return line


def _write(path: Path, header: str, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([f"[{header}]", *lines]) + "\n", encoding="utf-8")


class IngestLog:
    def __init__(self):
        self._stage: Stage | None = None
        self._lines: list[str] = []

    @contextmanager
    def stage(self, stage: Stage) -> Iterator[None]:
        """Logs a stage to its own file, even when it fails, with an ERROR line for the exception that stopped it."""
        self._stage = stage
        self._lines = []
        try:
            yield
        except Exception as e:
            self.writeline(f"{type(e).__name__}: {e}", level="ERROR")
            raise
        finally:
            self.dump()
            self._stage = None

    def writeline(self, message: str, level: Level = "INFO") -> None:
        """Prints the line, kept for the open stage's log if any."""
        line = _line(message, level)
        if self._stage is not None:
            self._lines.append(line)

    def dump(self) -> None:
        """Writes the stage's lines to its log file, replacing the last run's."""
        if self._stage is not None:
            _write(self._stage.log_file, self._stage.name.upper(), self._lines)


class PipelineLog:
    """Logs the run's steps and result to ingest/pipeline.log, however it ends."""

    def __init__(self) -> None:
        self._lines: list[str] = []
        self._step = "starting the run"
        self.promoted = False

    @contextmanager
    def run(self) -> Iterator[None]:
        self._lines = []
        try:
            yield
        except SystemExit as e:
            if e.code == ORPHANS_EXIT_CODE:
                self.writeline(f"Pipeline stopped while {self._step}: orphans await the resolve-subdivisions skill (see the subdivisions log); {self._outcome()}", level="WARN")
            else:
                self.writeline(f"Pipeline failed while {self._step}: {e.code}; {self._outcome()}", level="ERROR")
            raise
        except BaseException as e:
            self.writeline(f"Pipeline failed while {self._step}: {type(e).__name__}: {e}; {self._outcome()}", level="ERROR")
            raise
        else:
            self.writeline("Pipeline succeeded: build promoted")
        finally:
            _write(PIPELINE_LOG_PATH, "PIPELINE", self._lines)

    def _outcome(self) -> str:
        return "build promoted" if self.promoted else "nothing promoted"

    def step(self, doing: str) -> None:
        """Logs the step starting, which a failure is reported against."""
        self._step = doing
        self.writeline(doing[0].upper() + doing[1:])

    def writeline(self, message: str, level: Level = "INFO") -> None:
        self._lines.append(_line(message, level))


ingest_log = IngestLog()
pipeline_log = PipelineLog()
