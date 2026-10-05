from pathlib import Path
import pytest
from ingest.utils import logger, paths
from ingest.utils.logger import ORPHANS_EXIT_CODE, IngestLog, PipelineLog


def _log_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


class TestPipelineLog:
    """PIPELINE LOG"""

    def test_success(self, repo):
        """should log each step, then one line saying the build was promoted"""
        log = PipelineLog()

        with log.run():
            log.step("building demo")

        assert _log_lines(logger.PIPELINE_LOG_PATH) == ["[PIPELINE]", "[INFO] Building demo", "[INFO] Pipeline succeeded: build promoted"]

    def test_orphan_stop(self, repo):
        """should log an orphan stop as a warning against its step, with nothing promoted"""
        log = PipelineLog()

        with pytest.raises(SystemExit), log.run():
            log.step("building subdivisions")
            raise SystemExit(ORPHANS_EXIT_CODE)

        last = _log_lines(logger.PIPELINE_LOG_PATH)[-1]
        assert last.startswith("[WARN] Pipeline stopped while building subdivisions:")
        assert last.endswith("; nothing promoted")

    @pytest.mark.parametrize("promoted, outcome", [(False, "nothing promoted"), (True, "build promoted")])
    def test_failure(self, repo, promoted, outcome):
        """should log a failure as an error against its step, saying whether the build was promoted"""
        log = PipelineLog()

        with pytest.raises(RuntimeError), log.run():
            log.step("checking demo")
            log.promoted = promoted
            raise RuntimeError("boom")

        assert _log_lines(logger.PIPELINE_LOG_PATH)[-1] == f"[ERROR] Pipeline failed while checking demo: RuntimeError: boom; {outcome}"


class TestIngestLog:
    """INGEST LOG"""

    def test_stage_failure(self, repo):
        """should write a failed stage's log with an ERROR line for the exception that stopped it"""
        log = IngestLog()
        stage = paths.Stage("demo")

        with pytest.raises(RuntimeError), log.stage(stage):
            log.writeline("started")
            raise RuntimeError("boom")

        assert _log_lines(stage.log_file) == ["[DEMO]", "[INFO] started", "[ERROR] RuntimeError: boom"]

    def test_lines_outside_stage(self, repo):
        """should keep no line written after a stage ends for any stage's log"""
        log = IngestLog()
        stage = paths.Stage("demo")
        with log.stage(stage):
            log.writeline("inside")

        log.writeline("outside")
        with log.stage(paths.Stage("next")):
            pass

        assert _log_lines(stage.log_file) == ["[DEMO]", "[INFO] inside"]
        assert _log_lines(paths.Stage("next").log_file) == ["[NEXT]"]
