from pathlib import Path
import pytest
from ingest.utils import logger, paths, staging


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repo under tmp_path, with staging and the shipped data pointed into it."""
    staging_path = tmp_path / "ingest" / "staging"
    for name, value in {
        "REPO_PATH": tmp_path,
        "DATA_PATH": tmp_path / "data",
        "STAGING_PATH": staging_path,
        "STAGED_DATA_PATH": staging_path / "data",
        "STAGED_FILES_PATH": staging_path / "files",
        "FETCHED_PATH": staging_path / "fetched",
        "COMPLETE_MARKER": staging_path / "COMPLETE",
    }.items():
        monkeypatch.setattr(staging, name, value)
    monkeypatch.setattr(paths, "BASE_PATH", tmp_path / "ingest")
    monkeypatch.setattr(logger, "PIPELINE_LOG_PATH", tmp_path / "ingest" / "pipeline.log")
    return tmp_path


@pytest.fixture
def inputs(repo: Path) -> Path:
    return repo / "ingest" / "demo" / "inputs"


@pytest.fixture
def manifest(inputs: Path) -> Path:
    return inputs / "demo.manifest.json"
