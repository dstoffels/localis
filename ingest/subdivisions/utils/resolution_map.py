from dataclasses import dataclass, field, asdict
from pathlib import Path
import json


@dataclass
class AutoMergeMatch:
    id: int
    margin: int


@dataclass
class AuditEntry:
    id: int | None
    findings: str | None = None


@dataclass
class Orphans:
    no_candidates: list[str] = field(default_factory=list)
    no_matches: list[str] = field(default_factory=list)
    ambiguity: list[str] = field(default_factory=list)


@dataclass
class AutoMerge:
    bypassed: dict[str, int | None] = field(default_factory=dict)
    resolutions: dict[str, AutoMergeMatch] = field(default_factory=dict)
    orphans: Orphans = field(default_factory=Orphans)


@dataclass
class ResolutionMap:
    non_administrative_types: dict[str, list[str]] = field(default_factory=dict)
    audited: dict[str, AuditEntry] = field(default_factory=dict)
    skill_resolved: dict[str, int | None] = field(default_factory=dict)
    wikidata_merge: dict[str, int | None] = field(default_factory=dict)
    auto_merge: AutoMerge = field(default_factory=AutoMerge)

    @classmethod
    def load(cls, path: Path) -> "ResolutionMap":
        if not path.exists():
            return cls()

        data: dict[str, dict] = json.loads(path.read_text(encoding="utf-8"))
        auto_merge_data: dict = data.get("auto_merge", {})

        return cls(
            non_administrative_types=data.get("NON_ADMINISTRATIVE_TYPES", {}),
            audited={
                code: AuditEntry(**entry)
                for code, entry in data.get("audited", {}).items()
            },
            skill_resolved=data.get("skill_resolved", {}).get("resolutions", {}),
            wikidata_merge=data.get("wikidata_merge", {}).get("resolutions", {}),
            auto_merge=AutoMerge(
                bypassed=auto_merge_data.get("bypassed", {}),
                resolutions={
                    code: AutoMergeMatch(**match)
                    for code, match in auto_merge_data.get("resolutions", {}).items()
                },
                orphans=Orphans(**auto_merge_data.get("orphans", {})),
            ),
        )

    def save(self, path: Path) -> None:
        data = {
            "NON_ADMINISTRATIVE_TYPES": self.non_administrative_types,
            "audited": {code: asdict(entry) for code, entry in self.audited.items()},
            "skill_resolved": {"resolutions": self.skill_resolved},
            "wikidata_merge": {"resolutions": self.wikidata_merge},
            "auto_merge": {
                "bypassed": self.auto_merge.bypassed,
                "resolutions": {
                    code: asdict(match)
                    for code, match in self.auto_merge.resolutions.items()
                },
                "orphans": asdict(self.auto_merge.orphans),
            },
        }
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def is_non_administrative(self, alpha2: str, entry_type: str) -> bool:
        types = self.non_administrative_types.get(alpha2, [])
        return entry_type.lower() in {t.lower() for t in types}

    def reconcile(self, iso_code: str, result: AutoMergeMatch | None) -> bool:
        """True if a fresh result matches what's already in `audited` (caller discards it, nothing to write); evicts the stale audited entry otherwise, since the audit decision no longer reflects reality. An audited `id` of None means "verified: should not merge", which matches a fresh orphan result (also None)."""
        audited_entry = self.audited.get(iso_code)
        if audited_entry is None:
            return False
        fresh_id = result.id if result is not None else None
        if audited_entry.id == fresh_id:
            return True
        del self.audited[iso_code]
        return False
