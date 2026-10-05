import json
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar
from .logger import ingest_log
from .staging import staged_path, stage_text

V = TypeVar("V")

# queries per run that may disagree on which committed keys are missing before a removal counts as unconfirmed
CONFIRM_QUERIES = 4


class CommittedQuery(Generic[V]):
    """A live query's result (Wikidata has no ETag), staged each run and committed on promotion as its provenance."""

    def __init__(self, path: Path, label: str) -> None:
        self.path = path
        self.label = label

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def committed(self) -> dict[str, V]:
        """The last promoted build's result."""
        return self._read(self.path)

    def latest(self) -> dict[str, V]:
        """The last run's result, promoted or not."""
        staged = staged_path(self.path)
        return self._read(staged if staged.exists() else self.path)

    def fetch(self, query: Callable[[], dict[str, V]]) -> dict[str, V]:
        """Runs query and stages its result, accepting a removal of committed keys only once a repeat is missing the same ones."""
        committed_keys = self.committed().keys()
        result = query()
        removed = sorted(committed_keys - result.keys())
        queries = 1

        while removed:
            if queries == CONFIRM_QUERIES:
                raise RuntimeError(f"{self.label}'s missing committed keys kept changing across {queries} queries; try again later")
            ingest_log.writeline(f"{self.label} is missing {len(removed)} committed keys, querying again to confirm")
            result = query()
            queries += 1
            # only the missing keys must repeat, since the query service's servers lag by different amounts and the rest may differ
            unconfirmed, removed = removed, sorted(committed_keys - result.keys())
            if removed == unconfirmed:
                ingest_log.writeline(f"confirmed {len(removed)} {self.label} entries removed on Wikidata: {', '.join(removed)}", level="WARN")
                break

        stage_text(self.path, json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
        return result

    def log_changes(self, result: dict[str, V]) -> None:
        """Logs how result differs from the committed one."""
        committed = self.committed()
        if result == committed:
            return
        changed = sum(1 for key in result.keys() & committed.keys() if result[key] != committed[key])
        added = len(result.keys() - committed.keys())
        removed = len(committed.keys() - result.keys())
        ingest_log.writeline(f"{self.label} changed since the last promoted build: {changed} changed, {added} added, {removed} removed")
