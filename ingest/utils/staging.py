import shutil
from pathlib import Path
from .paths import REPO_PATH, DATA_PATH, STAGING_PATH, STAGED_DATA_PATH
from .download import commit_manifests
from .committed_query import CommittedQuery

# written once every stage has dumped, so a staged build is read as a whole only when it is complete
COMPLETE_MARKER = STAGING_PATH / "COMPLETE"
STAGED_FILES_PATH = STAGING_PATH / "files"


def reset_staging() -> None:
    """Clears the last run's staging at the start of a run; a failed run's staging is kept until then, since the skill reads it while orphans are open."""
    shutil.rmtree(STAGING_PATH, ignore_errors=True)
    STAGED_DATA_PATH.mkdir(parents=True)


def staged_path(path: Path) -> Path:
    """Where a repo file promoted with the data is staged: its repo-relative path under staging/files."""
    return STAGED_FILES_PATH / path.relative_to(REPO_PATH)


def stage_text(path: Path, text: str) -> None:
    """Stages text to be written to path on promotion."""
    staged = staged_path(path)
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.write_text(text, encoding="utf-8")


def mark_complete() -> None:
    COMPLETE_MARKER.touch()


def is_complete() -> bool:
    return COMPLETE_MARKER.exists()


def promote() -> None:
    """Moves the staged build into the repo: each registry's data directory, the staged repo files, the manifests and the committed Wikidata results, then clears staging."""
    if not is_complete():
        raise RuntimeError("staging holds no complete build to promote")
    for staged in sorted(STAGED_DATA_PATH.iterdir()):
        target = DATA_PATH / staged.name
        shutil.rmtree(target, ignore_errors=True)
        staged.rename(target)
    staged_files = STAGED_FILES_PATH.rglob("*") if STAGED_FILES_PATH.exists() else ()
    for staged in sorted(p for p in staged_files if p.is_file()):
        target = REPO_PATH / staged.relative_to(STAGED_FILES_PATH)
        target.parent.mkdir(parents=True, exist_ok=True)
        staged.replace(target)
    commit_manifests()
    CommittedQuery.commit_all()
    shutil.rmtree(STAGING_PATH)
