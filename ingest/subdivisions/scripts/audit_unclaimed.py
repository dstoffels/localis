from ingest.utils import SUBDIVISIONS_OUTPUTS_PATH, ingest_log
from ingest.subdivisions.utils.subdivision_map import SubdivisionMap
import json


def audit_unclaimed_geonames_subs(sub_map: SubdivisionMap) -> None:
    """Diagnostic: flag GeoNames-only subdivisions (no iso_code) sitting in a (country, admin_level) bucket where ISO does define subdivisions at that level, meaning this entry likely represents stale GeoNames data, a stale ISO entry, or a missed merge, rather than granularity ISO simply doesn't standardize."""
    subs = sub_map.all()

    iso_covered_buckets = {
        (sub.country.alpha2, sub.admin_level) for sub in subs if sub.iso_code is not None
    }

    unclaimed = [
        sub
        for sub in subs
        if sub.iso_code is None and (sub.country.alpha2, sub.admin_level) in iso_covered_buckets
    ]

    ingest_log.writeline(
        f"{len(unclaimed)} GeoNames-only subdivisions sit in a bucket where ISO has coverage at that admin level"
    )

    payload = {
        sub.geonames_code: {
            "name": sub.name,
            "aliases": sub.aliases,
            "country": sub.country.name,
            "admin_level": sub.admin_level,
        }
        for sub in unclaimed
    }
    (SUBDIVISIONS_OUTPUTS_PATH / "unclaimed_geonames_subdivisions.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
