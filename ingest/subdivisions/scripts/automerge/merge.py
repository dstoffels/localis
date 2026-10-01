from ingest.subdivisions.utils.strings import dedupe
from ingest.shared.models import SubdivisionModel


def merge_matched_sub(iso_sub: SubdivisionModel, geo_sub: SubdivisionModel) -> None:
    """Merge ISO subdivision data into the corresponding GeoNames subdivision."""
    geo_sub.type = iso_sub.type
    geo_sub.iso_code = iso_sub.iso_code
    geo_sub.admin_level = iso_sub.admin_level
    current_name = geo_sub.name
    if geo_sub.name != iso_sub.name and geo_sub.name not in geo_sub.aliases:
        geo_sub.aliases.append(current_name)
        geo_sub.name = iso_sub.name
    geo_sub.aliases.extend(iso_sub.aliases)
    geo_sub.aliases = dedupe(geo_sub.aliases)

    dupes = []
    for alt in geo_sub.aliases:
        if alt == geo_sub.name:
            dupes.append(alt)

    for d in dupes:
        geo_sub.aliases.remove(d)
