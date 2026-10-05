import importlib
import pytest
from ingest.shared.models import CountryModel, SubdivisionModel
from ingest.subdivisions.scripts.automerge import try_merge
from ingest.subdivisions.utils.resolution_map import ResolutionMap
from ingest.subdivisions.utils.subdivision_map import SubdivisionMap

COUNTRY = CountryModel(
    id=1, name="Testland", alpha2="TL", alpha3="TLD", geonames_id=None, official_name="Testland", common_name=None,
    aliases=[], numeric=None, flag=None, historic=None,
)


def _sub(name: str, aliases: list[str] | None = None, iso_code: str | None = None, geonames_id: int | None = None) -> SubdivisionModel:
    sub = SubdivisionModel(
        id=0, name=name, country=COUNTRY, type="Region", iso_code=iso_code, admin_level=1, aliases=aliases or [],
        geonames_code=f"TL.{geonames_id}" if geonames_id else None, geonames_id=geonames_id, parent=None,
    )
    sub.set_hashid()
    return sub


class TestTryMerge:
    """TRY MERGE"""

    def test_ambiguous_iso_code(self):
        """should keep an ISO code contesting an ambiguous GeoNames record as an ambiguity orphan, even when it also qualifies for another record"""
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

    def test_iso_code_only_qualifying_against_ambiguous_record(self):
        """should still merge an ISO code that only qualified against an ambiguous GeoNames record, below the ambiguity score, into its own match"""
        sub_map = SubdivisionMap()
        sub_map.add(_sub("Alpha", geonames_id=1))
        sub_map.add(_sub("Delta", geonames_id=3))
        iso_subs = {
            "TL-X": _sub("Alpha", iso_code="TL-X"),
            "TL-Y": _sub("Alpha", iso_code="TL-Y"),
            # scores 80 against Alpha, enough to qualify but short of the ambiguity score, and 100 against Delta
            "TL-Z": _sub("Alphx", aliases=["Delta"], iso_code="TL-Z"),
        }
        resolution_map = ResolutionMap()

        try_merge(iso_subs, sub_map, resolution_map)

        assert resolution_map.automerge.resolutions["TL-Z"].id == 3
        assert {o.iso_code for o in resolution_map.automerge.orphans.ambiguity} == {"TL-X", "TL-Y"}



class TestIsoCoverage:
    """ISO COVERAGE"""

    @staticmethod
    def _check(missing_orphan: bool) -> None:
        ingest_subdivisions = importlib.import_module("ingest.subdivisions.scripts.ingest_subdivisions")
        sub_map = SubdivisionMap()
        sub_map.add(_sub("Alpha", iso_code="TL-A", geonames_id=1))
        resolution_map = ResolutionMap()
        resolution_map.automerge.orphans.no_matches = ["TL-B"] if not missing_orphan else []
        ingest_subdivisions.check_iso_coverage({"TL-A", "TL-B"}, sub_map, resolution_map)

    def test_every_code_ships_or_awaits_skill(self):
        """should pass when every ISO code ships or is an orphan"""
        self._check(missing_orphan=False)

    def test_raises_on_dropped_code(self):
        """should raise on an ISO code that neither ships nor is an orphan"""
        with pytest.raises(ValueError):
            self._check(missing_orphan=True)
