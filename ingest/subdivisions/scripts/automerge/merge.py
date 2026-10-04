from ingest.utils.strings import dedupe
from ingest.shared.models import SubdivisionModel


def merge_matched_sub(iso_sub: SubdivisionModel, geo_sub: SubdivisionModel) -> None:
    """Merge ISO subdivision data into the corresponding GeoNames subdivision."""
    geo_sub.type = iso_sub.type
    geo_sub.iso_code = iso_sub.iso_code
    geo_sub.admin_level = iso_sub.admin_level
    geo_sub.parent_iso_code = iso_sub.parent_iso_code
    # ISO's name always wins; GeoNames' becomes an alias
    if geo_sub.name != iso_sub.name:
        geo_sub.aliases.append(geo_sub.name)
        geo_sub.name = iso_sub.name
    geo_sub.aliases = dedupe([*geo_sub.aliases, *iso_sub.aliases], exclude=(geo_sub.name,))
