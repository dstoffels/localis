# Stages docs/unmerged_subdivisions.md, every ISO subdivision without a GeoNames counterpart, promoted with the rest of each run's build.

from ingest.utils import DOCS_PATH, stage_text
from ingest.subdivisions.utils.subdivision_map import SubdivisionMap

DOC_PATH = DOCS_PATH / "unmerged_subdivisions.md"


def generate(sub_map: SubdivisionMap) -> str:
    unmerged = sorted(
        (s for s in sub_map.all() if s.iso_code is not None and s.geonames_id is None),
        key=lambda s: s.iso_code or "",
    )
    lines = [
        "# Unmerged subdivisions",
        "",
        f"{len(unmerged)} ISO 3166-2 subdivision(s) currently have no GeoNames counterpart.",
        "",
        "| ISO Code | Name | Country | Type |",
        "|---|---|---|---|",
    ]
    lines += [f"| {s.iso_code} | {s.name} | {s.country.name} | {s.type} |" for s in unmerged]
    return "\n".join(lines)


def write(sub_map: SubdivisionMap) -> None:
    stage_text(DOC_PATH, generate(sub_map))
