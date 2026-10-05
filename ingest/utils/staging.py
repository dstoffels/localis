import json
import shutil
from pathlib import Path
from .paths import REPO_PATH, DATA_PATH, STAGING_PATH, STAGED_DATA_PATH

# written once every stage has dumped, so a staged build is read as a whole only when it is complete
COMPLETE_MARKER = STAGING_PATH / "COMPLETE"
STAGED_FILES_PATH = STAGING_PATH / "files"
# the manifest entries staged by every run since the last promotion, so a rerun knows what inputs/ already holds instead of downloading it again
FETCHED_PATH = STAGING_PATH / "fetched"


def reset_staging() -> None:
    """Clears the last run's build at the start of a run, first merging its staged manifests into the fetched record; a failed run's staging is kept until then, since the skill reads it while orphans are open."""
    staged_manifests = STAGED_FILES_PATH.rglob("*.manifest.json") if STAGED_FILES_PATH.exists() else ()
    for staged in staged_manifests:
        fetched = FETCHED_PATH / staged.relative_to(STAGED_FILES_PATH)
        entries = json.loads(fetched.read_text(encoding="utf-8")) if fetched.exists() else {}
        entries.update(json.loads(staged.read_text(encoding="utf-8")))
        fetched.parent.mkdir(parents=True, exist_ok=True)
        fetched.write_text(json.dumps(dict(sorted(entries.items())), indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(STAGED_DATA_PATH, ignore_errors=True)
    shutil.rmtree(STAGED_FILES_PATH, ignore_errors=True)
    COMPLETE_MARKER.unlink(missing_ok=True)
    STAGED_DATA_PATH.mkdir(parents=True)


def staged_path(path: Path) -> Path:
    """Where a repo file promoted with the data is staged: its repo-relative path under staging/files."""
    return STAGED_FILES_PATH / path.relative_to(REPO_PATH)


def fetched_path(manifest_path: Path) -> Path:
    """The fetched record of a manifest: what runs since the last promotion downloaded into its stage's inputs/."""
    return FETCHED_PATH / manifest_path.relative_to(REPO_PATH)


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
    """Moves the staged build into the repo, each registry's data directory and every staged file (the manifests and committed Wikidata results among them), then clears staging."""
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
    shutil.rmtree(STAGING_PATH)
