import argparse
import gc
import json
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from tests.analysis.host import host_fingerprint

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = Path(__file__).with_name("footprint.json")
POPULATION_THRESHOLD = 15_000
REGISTRIES = ("countries", "subdivisions", "cities")
COMPONENTS = {"dataset": "_cache", "lookup_index": "_lookup_index", "filter_index": "_filter_index", "search_index": "_search_index"}
# a registry's views reference the registries before it, so their datasets load first and stay out of its measurement
DEPENDENCIES = {"countries": (), "subdivisions": ("countries",), "cities": ("countries", "subdivisions")}


def _rss_bytes() -> int:
    """Retained resident memory after a full collection, not the ru_maxrss peak."""
    gc.collect()
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    raise RuntimeError("VmRSS not found in /proc/self/status")


def _measure(load: Callable[[], object]) -> dict[str, float]:
    before = _rss_bytes()
    start = time.perf_counter()
    load()
    elapsed_ms = (time.perf_counter() - start) * 1000
    return {"time_ms": elapsed_ms, "memory_bytes": max(_rss_bytes() - before, 0)}


def _run_scenario(scenario: str) -> dict[str, Any]:
    """Runs one measurement in the current, fresh process."""
    import localis

    def preload(names: tuple[str, ...]) -> None:
        for name in names:
            _ = getattr(localis, name)._cache

    if scenario in REGISTRIES:
        preload(DEPENDENCIES[scenario])
        registry = getattr(localis, scenario)
        return {component: _measure(lambda attr=attr: getattr(registry, attr)) for component, attr in COMPONENTS.items()}
    if scenario == "cities_threshold":
        preload(DEPENDENCIES["cities"])
        localis.cities.set_population_threshold(POPULATION_THRESHOLD)
        result = _measure(localis.cities.force_cache)
        return {**result, "threshold": POPULATION_THRESHOLD, "count": len(localis.cities)}
    if scenario == "full_cache":
        return _measure(lambda: [getattr(localis, name).force_cache() for name in REGISTRIES])
    raise ValueError(f"unknown scenario: {scenario}")


def _median_runs(scenario: str, runs: int) -> dict[str, Any]:
    """Runs a scenario in `runs` fresh subprocesses and takes the median of every measured value."""
    results = []
    for _ in range(runs):
        out = subprocess.run(
            [sys.executable, "-m", "tests.analysis.footprint", "--scenario", scenario],
            cwd=ROOT, check=True, capture_output=True, text=True,
        ).stdout
        results.append(json.loads(out))

    def median_of(samples: list[Any]) -> Any:
        first = samples[0]
        if isinstance(first, dict):
            return {key: median_of([s[key] for s in samples]) for key in first}
        if isinstance(first, float):
            return round(statistics.median(samples), 3)
        if isinstance(first, int):
            return int(statistics.median(samples))
        return first

    return median_of(results)


def measure(runs: int, notes: str | None) -> dict[str, Any]:
    registries = {}
    for name in REGISTRIES:
        components = _median_runs(name, runs)
        components["combined"] = {
            "time_ms": round(sum(c["time_ms"] for c in components.values()), 3),
            "memory_bytes": sum(c["memory_bytes"] for c in components.values()),
        }
        registries[name] = components
    return {
        "host": host_fingerprint(),
        "runs": runs,
        "notes": notes,
        "registries": registries,
        "cities_threshold": _median_runs("cities_threshold", runs),
        "full_cache": _median_runs("full_cache", runs),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Measures load time and retained memory per registry component, appending to footprint.json.")
    parser.add_argument("--scenario", help=argparse.SUPPRESS)
    parser.add_argument("--runs", type=int, default=3, help="fresh-process runs per scenario; the median is kept")
    parser.add_argument("--notes", help="what changed since the last measurement")
    args = parser.parse_args()

    if args.scenario:
        print(json.dumps(_run_scenario(args.scenario)))
        return

    print(json.dumps(run(args.runs, args.notes), indent=2))


def run(runs: int = 3, notes: str | None = None) -> dict[str, Any]:
    """Measures every scenario and appends the result to footprint.json."""
    if not Path("/proc/self/status").exists():
        sys.exit("footprint measures retained memory from /proc/self/status, so it only runs on Linux")
    result = measure(runs, notes)
    history = json.loads(OUTPUT_PATH.read_text()) if OUTPUT_PATH.exists() else {}
    history[datetime.now().isoformat(timespec="seconds")] = result
    OUTPUT_PATH.write_text(json.dumps(history, indent=2) + "\n")
    return result


if __name__ == "__main__":
    main()
