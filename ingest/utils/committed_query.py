import json
from pathlib import Path
from typing import Any, Callable, ClassVar, Generic, TypeVar
from .download import SPARQL_ATTEMPTS
from .logger import ingest_log

V = TypeVar("V")


class CommittedQuery(Generic[V]):
    """A live query's result (Wikidata has no ETag), committed as its own provenance: each run's result is staged to a pending file and replaces the committed one only when the pipeline promotes its build."""

    # every instance, so promotion commits them all
    instances: ClassVar[list["CommittedQuery[Any]"]] = []

    def __init__(self, path: Path, label: str) -> None:
        self.path = path
        self.pending_path = path.with_suffix(".pending.json")
        self.label = label
        CommittedQuery.instances.append(self)

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def committed(self) -> dict[str, V]:
        """The result as of the last promoted build."""
        return self._read(self.path)

    def latest(self) -> dict[str, V]:
        """The result the last run fetched, committed or not."""
        return self._read(self.pending_path if self.pending_path.exists() else self.path)

    def fetch(self, query: Callable[[], dict[str, V]]) -> dict[str, V]:
        """Runs query and stages its result for commit(). A result missing committed keys is kept only once a repeat returns it unchanged: a Wikidata edit repeats, a flaky response doesn't."""
        committed_keys = self.committed().keys()
        result = query()
        queries = 1

        while removed := sorted(committed_keys - result.keys()):
            if queries == SPARQL_ATTEMPTS:
                raise RuntimeError(f"{self.label} results kept changing across {queries} queries; try again later")
            ingest_log.writeline(f"{self.label} is missing {len(removed)} committed keys, querying again to confirm")
            repeat = query()
            queries += 1
            if repeat == result:
                ingest_log.writeline(f"confirmed {len(removed)} {self.label} entries removed on Wikidata: {', '.join(removed)}", level="WARN")
                break
            result = repeat

        self.pending_path.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        return result

    def commit(self) -> None:
        """Replaces the committed result with this run's; called only on promotion."""
        if self.pending_path.exists():
            self.pending_path.replace(self.path)

    @classmethod
    def commit_all(cls) -> None:
        for query in cls.instances:
            query.commit()

    def log_changes(self, result: dict[str, V]) -> None:
        """Logs how result differs from the committed one, for the ingest PR."""
        committed = self.committed()
        if result == committed:
            return
        changed = sum(1 for key in result.keys() & committed.keys() if result[key] != committed[key])
        added = len(result.keys() - committed.keys())
        removed = len(committed.keys() - result.keys())
        ingest_log.writeline(f"{self.label} changed since the last promoted build: {changed} changed, {added} added, {removed} removed")
