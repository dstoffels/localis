from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Literal
import json


@dataclass
class AutomergeMatch:
    id: int
    margin: int


@dataclass
class AuditEntry:
    id: int | None
    findings: str | None = None


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
class Orphans:
    no_candidates: list[str] = field(default_factory=list)
    no_matches: list[str] = field(default_factory=list)
    ambiguity: list[AmbiguousOrphan] = field(default_factory=list)
    low_margin: list[LowMarginOrphan] = field(default_factory=list)
    wikidata_conflict: list[WikidataConflictOrphan] = field(default_factory=list)

    def count(self) -> int:
        return (
            len(self.no_candidates)
            + len(self.no_matches)
            + len(self.ambiguity)
            + len(self.low_margin)
            + len(self.wikidata_conflict)
        )

    def summary(self) -> str:
        return (
            f"no_candidates={len(self.no_candidates)}, no_matches={len(self.no_matches)}, ambiguity={len(self.ambiguity)}, "
            f"low_margin={len(self.low_margin)}, wikidata_conflict={len(self.wikidata_conflict)}"
        )


@dataclass
class Automerge:
    bypassed: dict[str, int | None] = field(default_factory=dict)
    resolutions: dict[str, AutomergeMatch] = field(default_factory=dict)
    geonames_absent: list[str] = field(default_factory=list)
    orphans: Orphans = field(default_factory=Orphans)


@dataclass
class ResolutionMap:
    non_administrative_types: dict[str, list[str]] = field(default_factory=dict)
    audited: dict[str, AuditEntry] = field(default_factory=dict)
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
            audited={
                code: AuditEntry(**entry)
                for code, entry in data.get("audited", {}).items()
            },
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
                orphans=Orphans(
                    no_candidates=automerge_data.get("orphans", {}).get("no_candidates", []),
                    no_matches=automerge_data.get("orphans", {}).get("no_matches", []),
                    ambiguity=[
                        AmbiguousOrphan(**orphan)
                        for orphan in automerge_data.get("orphans", {}).get("ambiguity", [])
                    ],
                    low_margin=[
                        LowMarginOrphan(**orphan)
                        for orphan in automerge_data.get("orphans", {}).get("low_margin", [])
                    ],
                    wikidata_conflict=[
                        WikidataConflictOrphan(**orphan)
                        for orphan in automerge_data.get("orphans", {}).get("wikidata_conflict", [])
                    ],
                ),
            ),
        )

    def save(self, path: Path) -> None:
        data = {
            "NON_ADMINISTRATIVE_TYPES": self.non_administrative_types,
            "audited": {code: asdict(entry) for code, entry in self.audited.items()},
            "skill_decisions": {code: asdict(decision) for code, decision in self.skill_decisions.items()},
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

    def reconcile(self, iso_code: str, geonames_id: int | None) -> bool:
        """True if a fresh geonames_id (or None, meaning no match) agrees with what's already in `audited` (caller discards it, nothing to write); evicts the stale audited entry otherwise, since the audit decision no longer reflects reality. An audited id of None means "verified: should not merge", which matches a fresh orphan result (also None). Shared by any recomputed-every-run source (automerge, wikidata_merge), not just AutomergeMatch."""
        audited_entry = self.audited.get(iso_code)
        if audited_entry is None:
            return False
        if audited_entry.id == geonames_id:
            return True
        del self.audited[iso_code]
        return False
