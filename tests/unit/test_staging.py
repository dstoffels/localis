from pathlib import Path
import pytest
from ingest.utils import staging
from utils import read_json, write_json


class TestResetStaging:
    """RESET STAGING"""

    def test_merges_staged_manifests(self, repo, manifest):
        """should merge the last run's staged manifests into the fetched record, its entries replacing older ones"""
        write_json(staging.fetched_path(manifest), {"a.txt": "older", "b.txt": "kept"})
        write_json(staging.staged_path(manifest), {"a.txt": "newer", "c.txt": "added"})

        staging.reset_staging()

        assert read_json(staging.fetched_path(manifest)) == {"a.txt": "newer", "b.txt": "kept", "c.txt": "added"}

    def test_clears_last_build(self, repo):
        """should clear the last run's staged data, staged files and completion marker"""
        staging.STAGED_DATA_PATH.joinpath("demo").mkdir(parents=True)
        staging.stage_text(repo / "docs" / "demo.md", "text")
        staging.mark_complete()

        staging.reset_staging()

        assert list(staging.STAGED_DATA_PATH.iterdir()) == []
        assert not staging.STAGED_FILES_PATH.exists()
        assert not staging.is_complete()


class TestPromote:
    """PROMOTE"""

    @staticmethod
    def _stage_build(repo: Path) -> None:
        for registry, file in (("demo", "old.tsv"), ("other", "other.tsv")):
            (staging.DATA_PATH / registry).mkdir(parents=True)
            (staging.DATA_PATH / registry / file).write_text("shipped")
        (staging.STAGED_DATA_PATH / "demo").mkdir(parents=True)
        (staging.STAGED_DATA_PATH / "demo" / "new.tsv").write_text("staged")
        staging.stage_text(repo / "docs" / "demo.md", "staged")

    def test_refuses_incomplete_build(self, repo):
        """should promote nothing from a build no run marked complete"""
        self._stage_build(repo)

        with pytest.raises(RuntimeError):
            staging.promote()
        assert (staging.DATA_PATH / "demo" / "old.tsv").exists()
        assert not (repo / "docs" / "demo.md").exists()

    def test_moves_build(self, repo, manifest):
        """should replace each staged registry's shipped data, move the staged files to their repo paths and clear staging"""
        self._stage_build(repo)
        write_json(staging.fetched_path(manifest), {})
        staging.mark_complete()

        staging.promote()

        assert [p.name for p in (staging.DATA_PATH / "demo").iterdir()] == ["new.tsv"]
        assert (staging.DATA_PATH / "other" / "other.tsv").exists()
        assert (repo / "docs" / "demo.md").read_text() == "staged"
        assert not staging.STAGING_PATH.exists()
