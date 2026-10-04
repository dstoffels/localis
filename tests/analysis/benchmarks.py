import argparse
import json
import random
import statistics
import time
import zlib
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
import localis
from localis.entities import Entity
from localis.registries import QueryableRegistry
from localis.utils.strings import is_latin
from tests.analysis.host import host_fingerprint
from tests.utils import mangle

OUTPUT_PATH = Path(__file__).with_name("benchmarks.json")
FAILURES_LOG_PATH = Path(__file__).with_name("search_failures.log")
REGISTRIES = ("countries", "subdivisions", "cities")
SAMPLE_SIZE = 5000
SEED = 0


def _search_query(entry: Entity) -> str:
    if isinstance(entry, localis.City):
        admin1 = next((s for s in entry.subdivisions if s.admin_level == 1), None)
        if admin1:
            return f"{entry.name} {admin1.name}"
    return entry.name


def _stable_seed(*parts: object) -> int:
    """A seed that's the same in every process, unlike hash() on strings."""
    return zlib.crc32(":".join(map(str, parts)).encode())


def _timed(call: Callable[[], Any], samples: list[float]) -> Any:
    start = time.perf_counter()
    result = call()
    samples.append((time.perf_counter() - start) * 1000)
    return result


def _percentiles(samples: list[float]) -> dict[str, float]:
    cuts = statistics.quantiles(samples, n=100, method="inclusive")
    return {
        "p50_ms": round(cuts[49], 4),
        "p95_ms": round(cuts[94], 4),
        "p99_ms": round(cuts[98], 4),
        "max_ms": round(max(samples), 4),
    }


def benchmark_registry(
    name: str, sample_size: int, iterations: int, log
) -> dict[str, Any]:
    """Search's per-call latency percentiles on warm caches, and its accuracy (top-10 hit rate, top-1 rate, mean reciprocal rank) on mangled names and aliases; get, lookup and filter are index reads too fast to be worth timing."""
    registry: QueryableRegistry = getattr(localis, name)
    registry.force_cache()
    entries: list[Entity] = list(registry)
    latency: list[float] = []
    hits, misses, top1, reciprocal_ranks, hit_scores = 0, 0, 0, 0.0, []

    def search(query: str, entry: Entity, query_type: str, seed: int) -> None:
        nonlocal hits, misses, top1, reciprocal_ranks
        # mangle() inserts Latin letters, so it can't simulate a typo in any other script
        if not is_latin(query):
            return
        mangled = mangle(query, seed=seed)
        results = _timed(lambda: registry.search(mangled), latency)
        rank = next(
            (i for i, (r, _) in enumerate(results, start=1) if r.id == entry.id), None
        )
        if rank is not None:
            hits += 1
            top1 += rank == 1
            reciprocal_ranks += 1 / rank
            hit_scores.append(results[rank - 1][1])
            return
        misses += 1
        top = (
            f'"{results[0][0].name}" ({results[0][1]:.2f})' if results else "no results"
        )
        log.write(
            f'[{name}:{query_type}] "{mangled}" -> expected "{query}" (id={entry.id}), got {top}\n'
        )

    for i in range(iterations):
        rng = random.Random(SEED + i)
        for entry in rng.sample(entries, min(sample_size, len(entries))):
            search(
                _search_query(entry),
                entry,
                "name",
                seed=_stable_seed(entry.id, i, "name"),
            )
            # drawn from Latin-script aliases only, so a record is never skipped for drawing one mangle() can't typo
            aliases = [a for a in getattr(entry, "aliases", ()) if is_latin(a)]
            if aliases:
                alias = random.Random(_stable_seed(entry.id, i)).choice(aliases)
                search(alias, entry, "alias", seed=_stable_seed(entry.id, i, "alias"))

    queries = hits + misses
    return {
        "search": _percentiles(latency),
        "accuracy": {
            "queries": queries,
            "failures": misses,
            "success_pct": round(100 * hits / queries, 1) if queries else 0.0,
            # top-10 hits alone can't see a ranking regression, since candidate selection can still surface the right entry
            "top1_pct": round(100 * top1 / queries, 1) if queries else 0.0,
            "mrr": round(reciprocal_ranks / queries, 3) if queries else 0.0,
            "avg_hit_score": round(sum(hit_scores) / hits, 3) if hits else 0.0,
        },
    }


def benchmark(sample_size: int, iterations: int, notes: str | None) -> dict[str, Any]:
    with open(FAILURES_LOG_PATH, "w") as log:
        log.write(
            f"# search failures - sample {sample_size} x {iterations}, seed {SEED}\n"
        )
        registries = {}
        for name in REGISTRIES:
            print(f"Benchmarking {name}...")
            registries[name] = benchmark_registry(name, sample_size, iterations, log)
    return {
        "host": host_fingerprint(),
        "sample_size": sample_size,
        "iterations": iterations,
        "seed": SEED,
        "notes": notes,
        "registries": registries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmarks query latency percentiles and search accuracy, appending to benchmarks.json."
    )
    parser.add_argument("--sample-size", type=int, default=SAMPLE_SIZE)
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--notes", help="what changed since the last benchmark")
    args = parser.parse_args()

    print(json.dumps(run(args.sample_size, args.iterations, args.notes), indent=2))


def run(
    sample_size: int = SAMPLE_SIZE, iterations: int = 1, notes: str | None = None
) -> dict[str, Any]:
    """Benchmarks every registry and appends the result to benchmarks.json."""
    result = benchmark(sample_size, iterations, notes)
    history = json.loads(OUTPUT_PATH.read_text()) if OUTPUT_PATH.exists() else {}
    history[datetime.now().isoformat(timespec="seconds")] = result
    OUTPUT_PATH.write_text(json.dumps(history, indent=2) + "\n")
    return result


if __name__ == "__main__":
    main()
