import json
import re
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_PATH = Path(__file__).parent
DOCS = [ROOT / "README.md", ROOT / "docs" / "methodology.md", ROOT / "docs" / "dev.md"]
# data_stats.json is overwritten per ingest; footprint.json and benchmarks.json are histories, rendered from their latest entry
SOURCES = {
    "data": "data_stats.json",
    "footprint": "footprint.json",
    "bench": "benchmarks.json",
}
HISTORY_SOURCES = {"footprint", "bench"}
# only deterministic numbers are checked; timings and memory vary by host
CHECKED_SOURCES = {"data"}
# the format follows a colon, not a pipe, since a pipe would split the marker across markdown table cells
# a value can't contain another tag, so an unclosed example tag in prose never pairs with a later tag's close
MARKER_RE = re.compile(
    r'<stat key="([a-z_]+)\.([\w.]+)(?::(\w+))?">((?:(?!</?stat\b).)*)</stat>'
)


def _load_time(ms: float) -> str:
    if ms < 1:
        return "< 1ms"
    return f"~{ms:.0f}ms" if ms < 1000 else f"~{ms / 1000:.2f}s"


def _size(size_bytes: float) -> str:
    # decimal units, as the KB and MB labels mean
    return (
        f"{size_bytes / 1000:.0f}KB"
        if size_bytes < 1000**2
        else f"{size_bytes / 1000**2:.1f}MB"
    )


FORMATS: dict[str, Callable[[Any], str]] = {
    "raw": str,
    "int": lambda v: f"{int(v):,}",
    "pct": lambda v: f"{v:.1f}%",
    "load": _load_time,
    "size": _size,
    "latency": lambda v: f"{v:.3g}ms",
}


def _load_sources() -> dict[str, Any]:
    sources: dict[str, Any] = {}
    for name, filename in SOURCES.items():
        path = ANALYSIS_PATH / filename
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        sources[name] = data[max(data)] if name in HISTORY_SOURCES and data else data
    return sources


def _value(sources: dict[str, Any], source: str, key: str) -> Any:
    node, parts = sources[source], key.split(".")
    while parts:
        # a key can itself contain dots (file names like cities.tsv), so take the shortest run of parts that names a key
        for n in range(1, len(parts) + 1):
            candidate = ".".join(parts[:n])
            if candidate in node:
                node, parts = node[candidate], parts[n:]
                break
        else:
            raise KeyError(parts[0])
    return node


def render(
    text: str, sources: dict[str, Any], stale: list[str] | None = None, doc: str = ""
) -> str:
    """Fills every stat marker in text from the sources; a marker whose source file doesn't exist yet is left as-is. Records checked markers that changed in `stale`."""

    def replace(match: re.Match[str]) -> str:
        source, key, fmt, current = (
            match.group(1),
            match.group(2),
            match.group(3) or "raw",
            match.group(4),
        )
        if source not in SOURCES:
            raise KeyError(f"{doc}: unknown stat source '{source}' in marker for {key}")
        if source not in sources:
            return match.group(0)
        if fmt not in FORMATS:
            raise KeyError(
                f"{doc}: unknown stat format '{fmt}' in marker for {source}.{key}"
            )
        try:
            value = _value(sources, source, key)
        except KeyError as e:
            # a metric added since the latest footprint/benchmark run stays as-is until the next run measures it
            if source in HISTORY_SOURCES:
                print(f"{doc}: {source}.{key} not in the latest run yet, left as-is")
                return match.group(0)
            raise KeyError(
                f"{doc}: stat marker {source}.{key}:{fmt} doesn't resolve ({e})"
            ) from e
        rendered = FORMATS[fmt](value)
        if stale is not None and source in CHECKED_SOURCES and rendered != current:
            stale.append(f"{doc}: {source}.{key} is '{current}', expected '{rendered}'")
        whole, offset = match.group(0), match.start(0)
        return (
            whole[: match.start(4) - offset] + rendered + whole[match.end(4) - offset :]
        )

    return MARKER_RE.sub(replace, text)


def check() -> list[str]:
    """Stale deterministic markers across the docs, empty if all are current; a checked source that's missing counts as stale."""
    sources = _load_sources()
    stale = [f"{SOURCES[name]} is missing, so no {name} marker can be checked" for name in sorted(CHECKED_SOURCES) if name not in sources]
    for doc in DOCS:
        render(
            doc.read_text(encoding="utf-8"),
            sources,
            stale,
            doc.relative_to(ROOT).as_posix(),
        )
    return stale


def render_all() -> list[str]:
    """Fills the markers in every doc, returning the docs that changed."""
    sources = _load_sources()
    updated = []
    for doc in DOCS:
        text = doc.read_text(encoding="utf-8")
        rendered = render(text, sources, doc=doc.relative_to(ROOT).as_posix())
        if rendered != text:
            doc.write_text(rendered, encoding="utf-8")
            updated.append(doc.relative_to(ROOT).as_posix())
    return updated
