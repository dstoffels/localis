# Generates docs/unmerged_subdivisions.md: every ISO-sourced subdivision currently
# without a GeoNames geonames_id, written fresh from the final dataset on every ingest run.

from ingest.utils import DOCS_PATH
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
    DOC_PATH.write_text(generate(sub_map), encoding="utf-8")
