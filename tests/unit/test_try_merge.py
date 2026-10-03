from ingest.shared.models import CountryModel, SubdivisionModel
from ingest.subdivisions.scripts.automerge import try_merge
from ingest.subdivisions.utils.resolution_map import ResolutionMap
from ingest.subdivisions.utils.subdivision_map import SubdivisionMap

COUNTRY = CountryModel(
    id=1, name="Testland", alpha2="TL", alpha3="TLD", geonames_id=None, official_name="Testland",
    aliases=[], numeric=None, flag=None, historic=None,
)


def _sub(name: str, aliases: list[str] | None = None, iso_code: str | None = None, geonames_id: int | None = None) -> SubdivisionModel:
    sub = SubdivisionModel(
        id=0, name=name, country=COUNTRY, type="Region", iso_code=iso_code, admin_level=1, aliases=aliases or [],
        geonames_code=f"TL.{geonames_id}" if geonames_id else None, geonames_id=geonames_id, parent=None,
    )
    sub.set_hashid()
    assert sub.hashid is not None
    sub.id = sub.hashid
    return sub


def test_ambiguous_iso_code_is_not_merged_elsewhere():
    """an ISO code contesting an ambiguous GeoNames record stays an ambiguity orphan even when it also qualifies for another record"""
    sub_map = SubdivisionMap()
    sub_map.add(_sub("Alpha", geonames_id=1))
    sub_map.add(_sub("Gamma", geonames_id=2))
    iso_subs = {
        # both score 100 against Alpha, making it ambiguous; TL-X also matches Gamma through its alias
        "TL-X": _sub("Alpha", aliases=["Gamma"], iso_code="TL-X"),
        "TL-Y": _sub("Alpha", iso_code="TL-Y"),
    }
    resolution_map = ResolutionMap()

    try_merge(iso_subs, sub_map, resolution_map)

    assert "TL-X" not in resolution_map.automerge.resolutions
    assert {o.iso_code for o in resolution_map.automerge.orphans.ambiguity} == {"TL-X", "TL-Y"}
