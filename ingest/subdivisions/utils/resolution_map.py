from dataclasses import dataclass, field, fields, asdict
from pathlib import Path
from typing import Literal, get_args, get_type_hints
import json


@dataclass
class AutomergeMatch:
    id: int
    margin: int


@dataclass
class SkillDecision:
    """A resolve-subdivisions decision: a GeoNames id to merge into, or None for "add as-is". escalation holds the agent's findings when it sent the orphan to a human. wikidata_seen is the Wikidata crosswalk's mapping when the decision was made, so a decision that disagrees with it is a known override rather than a silent one. reason and decided_by are None for decisions recorded before they were tracked."""

    id: int | None
    reason: str | None = None
    decided_by: Literal["agent", "human"] | None = None
    escalation: str | None = None
    wikidata_seen: int | None = None


@dataclass
class AmbiguousOrphan:
    iso_code: str
    candidate_geonames_ids: list[int]


@dataclass
class LowMarginOrphan:
    iso_code: str
    candidate_geonames_id: int
    margin: int


@dataclass
class WikidataConflictOrphan:
    iso_code: str
    wikidata_geonames_id: int
    decision_geonames_id: int | None


@dataclass
class WikidataChangedOrphan:
    iso_code: str
    previous_geonames_id: int
    wikidata_geonames_id: int


@dataclass
class GroupingTwinOrphan:
    iso_code: str
    candidate_geonames_id: int


# a no_candidates/no_matches orphan is its bare iso_code; the flagged buckets carry what the pipeline found
OrphanEntry = (
    str
    | AmbiguousOrphan
    | LowMarginOrphan
    | WikidataConflictOrphan
    | WikidataChangedOrphan
    | GroupingTwinOrphan
)


def _iso_code(entry: OrphanEntry) -> str:
    return entry if isinstance(entry, str) else entry.iso_code


@dataclass
class Orphans:
    """The ISO subdivisions awaiting the resolve-subdivisions skill, by why they were orphaned; buckets are reviewed in field order."""

    no_candidates: list[str] = field(default_factory=list)
    no_matches: list[str] = field(default_factory=list)
    ambiguity: list[AmbiguousOrphan] = field(default_factory=list)
    low_margin: list[LowMarginOrphan] = field(default_factory=list)
    wikidata_conflict: list[WikidataConflictOrphan] = field(default_factory=list)
    wikidata_changed: list[WikidataChangedOrphan] = field(default_factory=list)
    grouping_twin: list[GroupingTwinOrphan] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, list]) -> "Orphans":
        """Rebuilds each bucket's entries as the type its field declares."""
        hints = get_type_hints(cls)
        buckets = {}
        for f in fields(cls):
            (entry_type,) = get_args(hints[f.name])
            entries = data.get(f.name, [])
            buckets[f.name] = (
                entries
                if entry_type is str
                else [entry_type(**entry) for entry in entries]
            )
        return cls(**buckets)

    def _buckets(self) -> dict[str, list[OrphanEntry]]:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def count(self) -> int:
        return sum(len(bucket) for bucket in self._buckets().values())

    def summary(self) -> str:
        return ", ".join(
            f"{name}={len(bucket)}" for name, bucket in self._buckets().items()
        )

    def codes(self) -> list[str]:
        """Every orphan's iso_code, in review order."""
        return [
            _iso_code(entry) for bucket in self._buckets().values() for entry in bucket
        ]

    def find(self, iso_code: str) -> OrphanEntry | None:
        return next(
            (
                entry
                for bucket in self._buckets().values()
                for entry in bucket
                if _iso_code(entry) == iso_code
            ),
            None,
        )

    def remove(self, iso_code: str) -> None:
        for bucket in self._buckets().values():
            for entry in bucket:
                if _iso_code(entry) == iso_code:
                    bucket.remove(entry)
                    return
        raise ValueError(f"{iso_code} is not in resolution_map's orphans")


@dataclass
class Automerge:
    bypassed: dict[str, int | None] = field(default_factory=dict)
    resolutions: dict[str, AutomergeMatch] = field(default_factory=dict)
    geonames_absent: list[str] = field(default_factory=list)
    orphans: Orphans = field(default_factory=Orphans)


@dataclass
class ResolutionMap:
    non_administrative_types: dict[str, list[str]] = field(default_factory=dict)
    skill_decisions: dict[str, SkillDecision] = field(default_factory=dict)
    wikidata_merge: dict[str, int | None] = field(default_factory=dict)
    automerge: Automerge = field(default_factory=Automerge)

    @classmethod
    def load(cls, path: Path) -> "ResolutionMap":
        if not path.exists():
            return cls()

        data: dict[str, dict] = json.loads(path.read_text(encoding="utf-8"))
        automerge_data: dict = data.get("automerge", {})

        return cls(
            non_administrative_types=data.get("NON_ADMINISTRATIVE_TYPES", {}),
            skill_decisions={
                code: SkillDecision(**decision)
                for code, decision in data.get("skill_decisions", {}).items()
            },
            wikidata_merge=data.get("wikidata_merge", {}),
            automerge=Automerge(
                bypassed=automerge_data.get("bypassed", {}),
                resolutions={
                    code: AutomergeMatch(**match)
                    for code, match in automerge_data.get("resolutions", {}).items()
                },
                geonames_absent=automerge_data.get("geonames_absent", []),
                orphans=Orphans.from_dict(automerge_data.get("orphans", {})),
            ),
        )

    def save(self, path: Path) -> None:
        data = {
            "NON_ADMINISTRATIVE_TYPES": self.non_administrative_types,
            "skill_decisions": {
                code: asdict(decision)
                for code, decision in self.skill_decisions.items()
            },
            "wikidata_merge": self.wikidata_merge,
            "automerge": {
                "bypassed": self.automerge.bypassed,
                "resolutions": {
                    code: asdict(match)
                    for code, match in self.automerge.resolutions.items()
                },
                "geonames_absent": self.automerge.geonames_absent,
                "orphans": asdict(self.automerge.orphans),
            },
        }
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def is_non_administrative(self, alpha2: str, entry_type: str) -> bool:
        types = self.non_administrative_types.get(alpha2, [])
        return entry_type.lower() in {t.lower() for t in types}
