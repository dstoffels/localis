# Reports on subdivisions the resolve-subdivisions skill hasn't resolved yet.
# Used by the ingest CI workflow to decide whether to block the PR.

from ingest.utils import SUBDIVISIONS_OUTPUTS_PATH
import json
import sys

ORPHANED_PATH = SUBDIVISIONS_OUTPUTS_PATH / "orphaned_subdivisions.json"


def load_orphans() -> dict:
    if not ORPHANED_PATH.exists():
        return {}
    return json.loads(ORPHANED_PATH.read_text(encoding="utf-8")) or {}


def summarize(orphans: dict) -> str:
    lines = [f"**{len(orphans)} orphaned subdivision(s) need manual resolution:**", ""]
    lines += [
        f"- `{iso_code}`: {entry['name']} ({entry['country']})"
        for iso_code, entry in orphans.items()
    ]
    lines += [
        "",
        "Pull the `ingest` branch, run the resolve-subdivisions skill to resolve these, "
        "then commit and push back to `origin/ingest` to re-trigger this workflow.",
    ]
    return "\n".join(lines)


def main() -> None:
    orphans = load_orphans()
    if not orphans:
        sys.exit(0)
    print(summarize(orphans))
    sys.exit(1)


if __name__ == "__main__":
    main()
