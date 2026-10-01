# Reports on subdivisions the resolve-subdivisions skill hasn't resolved yet.
# Used by the ingest CI workflow to decide whether to block the PR.

from ingest.utils import SUBDIVISIONS_OUTPUTS_PATH
from ingest.subdivisions.utils.resolution_map import ResolutionMap, Orphans
import sys

RESOLUTION_MAP_PATH = SUBDIVISIONS_OUTPUTS_PATH / "resolution_map.json"


def load_orphans() -> Orphans:
    return ResolutionMap.load(RESOLUTION_MAP_PATH).auto_merge.orphans


def summarize(orphans: Orphans) -> str:
    ambiguity_codes = [orphan.iso_code for orphan in orphans.ambiguity]
    total = len(orphans.no_candidates) + len(orphans.no_matches) + len(ambiguity_codes)
    lines = [f"**{total} orphaned subdivision(s) need manual resolution:**", ""]
    for reason, codes in (
        ("no candidates", orphans.no_candidates),
        ("no matches", orphans.no_matches),
        ("ambiguous", ambiguity_codes),
    ):
        if codes:
            lines.append(f"- {reason}: {', '.join(codes)}")
    lines += [
        "",
        "Pull the `ingest` branch, run the resolve-subdivisions skill to resolve these, "
        "then commit and push back to `origin/ingest` to re-trigger this workflow.",
    ]
    return "\n".join(lines)


def main() -> None:
    orphans = load_orphans()
    total = len(orphans.no_candidates) + len(orphans.no_matches) + len(orphans.ambiguity)
    if not total:
        sys.exit(0)
    print(summarize(orphans))
    sys.exit(1)


if __name__ == "__main__":
    main()
