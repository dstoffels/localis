import importlib
import pytest
from ingest.shared.models import CountryModel, SubdivisionModel
from ingest.subdivisions.scripts.automerge import try_merge
from ingest.subdivisions.scripts.resolve_subdivisions import apply_skill_decisions, flag_new_candidates, retire_decisions
from ingest.subdivisions.utils.resolution_map import ResolutionMap, SkillDecision
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


class TestDedupeAliases:
    """DEDUPE ALIASES"""

    def test_drops_variants_of_name(self):
        """should drop an alias that is a case or accent variant of the subdivision's own name, keeping the rest"""
        ingest_subdivisions = importlib.import_module("ingest.subdivisions.scripts.ingest_subdivisions")
        sub_map = SubdivisionMap()
        sub = _sub("Dōshī Kanton", aliases=["Doshi kanton", "Doshi"], geonames_id=1)
        sub_map.add(sub)

        ingest_subdivisions.dedupe_aliases(sub_map)

        assert sub.aliases == ["Doshi"]


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


class TestRetireDecisions:
    """RETIRE DECISIONS"""

    def test_retires_removed_and_bypassed(self):
        """should move a decision whose code left ISO or is now bypassed to retired_decisions with why, keeping the rest live"""
        resolution_map = ResolutionMap(skill_decisions={"TL-1": SkillDecision(id=1), "TL-2": SkillDecision(id=None), "TL-3": SkillDecision(id=3)})

        retire_decisions(resolution_map, build_codes={"TL-1", "TL-3"}, bypassed_codes={"TL-3"})

        assert set(resolution_map.skill_decisions) == {"TL-1"}
        assert resolution_map.retired_decisions["TL-2"].retired_because == "removed_from_iso"
        assert resolution_map.retired_decisions["TL-3"].retired_because == "bypassed"
        assert resolution_map.retired_decisions["TL-3"].decision.id == 3

    def test_round_trip(self, tmp_path):
        """should save and load retired decisions and candidates_seen unchanged"""
        resolution_map = ResolutionMap(skill_decisions={"TL-1": SkillDecision(id=None, candidates_seen=[7]), "TL-2": SkillDecision(id=2)})
        retire_decisions(resolution_map, build_codes={"TL-1"}, bypassed_codes=set())
        path = tmp_path / "resolution_map.json"

        resolution_map.save(path)
        loaded = ResolutionMap.load(path)

        assert loaded.skill_decisions == resolution_map.skill_decisions
        assert loaded.retired_decisions == resolution_map.retired_decisions


class TestApplySkillDecisions:
    """APPLY SKILL DECISIONS"""

    def test_applies_valid_decisions(self):
        """should merge a decision into its target, add an add-as-is one, and return only the codes with no decision"""
        sub_map = SubdivisionMap()
        sub_map.add(_sub("Alpha", geonames_id=1))
        iso_subs = {code: _sub(name, iso_code=code) for code, name in (("TL-A", "Alpha"), ("TL-B", "Beta"), ("TL-C", "Gamma"))}
        resolution_map = ResolutionMap(skill_decisions={"TL-A": SkillDecision(id=1), "TL-B": SkillDecision(id=None)})

        remaining = apply_skill_decisions(iso_subs, resolution_map, sub_map)

        assert set(remaining) == {"TL-C"}
        target = sub_map.get(geonames_id=1)
        assert target is not None and target.iso_code == "TL-A"
        assert resolution_map.automerge.orphans.count() == 0

    def test_stale_decision(self):
        """should send a merge whose target is gone back for review, never to Wikidata or automerge"""
        iso_subs = {"TL-A": _sub("Alpha", iso_code="TL-A")}
        resolution_map = ResolutionMap(skill_decisions={"TL-A": SkillDecision(id=99)})

        remaining = apply_skill_decisions(iso_subs, resolution_map, SubdivisionMap())

        assert not remaining
        assert [o.iso_code for o in resolution_map.automerge.orphans.stale_decision] == ["TL-A"]

    def test_contested_decision(self):
        """should send every decision naming the same target back for review, applying none of them"""
        sub_map = SubdivisionMap()
        sub_map.add(_sub("Alpha", geonames_id=1))
        iso_subs = {code: _sub("Alpha", iso_code=code) for code in ("TL-A", "TL-B")}
        resolution_map = ResolutionMap(skill_decisions={"TL-A": SkillDecision(id=1), "TL-B": SkillDecision(id=1)})

        remaining = apply_skill_decisions(iso_subs, resolution_map, sub_map)

        assert not remaining
        contested = {o.iso_code: o.contested_with for o in resolution_map.automerge.orphans.contested_decision}
        assert contested == {"TL-A": ["TL-B"], "TL-B": ["TL-A"]}
        target = sub_map.get(geonames_id=1)
        assert target is not None and target.iso_code is None


class TestFlagNewCandidates:
    """FLAG NEW CANDIDATES"""

    @staticmethod
    def _added(candidates_seen: list[int] | None) -> tuple[dict[str, SubdivisionModel], ResolutionMap, SubdivisionMap]:
        """An applied add decision for TL-A, with an unclaimed GeoNames record that qualifies for it."""
        iso_sub = _sub("Alpha", iso_code="TL-A")
        sub_map = SubdivisionMap()
        sub_map.add(iso_sub)
        sub_map.add(_sub("Alpha", geonames_id=1))
        resolution_map = ResolutionMap(skill_decisions={"TL-A": SkillDecision(id=None, candidates_seen=candidates_seen)})
        return {"TL-A": iso_sub}, resolution_map, sub_map

    def test_records_baseline(self):
        """should record an add's qualifying records as its baseline when it has none, without reopening it"""
        iso_subs, resolution_map, sub_map = self._added(None)

        flag_new_candidates(iso_subs, resolution_map, sub_map)

        assert resolution_map.skill_decisions["TL-A"].candidates_seen == [1]
        assert not resolution_map.automerge.orphans.new_candidate

    def test_reopens_for_new_record(self):
        """should send an add back for review when a record qualifies that it wasn't decided against"""
        iso_subs, resolution_map, sub_map = self._added([])

        flag_new_candidates(iso_subs, resolution_map, sub_map)

        assert [(o.iso_code, o.candidate_geonames_ids) for o in resolution_map.automerge.orphans.new_candidate] == [("TL-A", [1])]

    def test_keeps_seen_record(self):
        """should leave an add alone when every qualifying record was among its candidates_seen"""
        iso_subs, resolution_map, sub_map = self._added([1])

        flag_new_candidates(iso_subs, resolution_map, sub_map)

        assert not resolution_map.automerge.orphans.new_candidate
