import argparse
import sys
from pathlib import Path
from typing import Any
from tests.analysis import benchmarks, data_stats, footprint, render_docs

ROOT = data_stats.ROOT


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _records(stats: dict[str, Any]) -> str:
    return f"{stats['totals']['records']:,} records across {len(data_stats.REGISTRY_STATS)} registries"


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="analysis",
        description="Runs the analysis suite: data stats, footprint and benchmarks, then fills the docs' stat markers.",
    )
    parser.add_argument("--data-only", action="store_true", help="only the deterministic data stats and docs, as CI runs after ingest")
    parser.add_argument("--staging", action="store_true", help="only check that the pipeline's complete staged build reconciles, as its reconcile gate does; writes nothing")
    parser.add_argument("--check", action="store_true", help="only check that the docs' deterministic markers are current; writes nothing")
    parser.add_argument("--notes", help="what changed since the last footprint and benchmark run")
    parser.add_argument("--runs", type=int, default=3, help="fresh-process runs per footprint scenario")
    parser.add_argument("--sample-size", type=int, default=benchmarks.SAMPLE_SIZE, help="entries sampled per registry for benchmarks")
    parser.add_argument("--iterations", type=int, default=1, help="benchmark passes per registry")
    args = parser.parse_args()

    if args.check:
        stale = render_docs.check()
        for line in stale:
            print(line)
        sys.exit(1 if stale else 0)

    if args.staging:
        data_stats.use_staging()
        print(f"Checking the data stats of the staged build ({_relative(data_stats.DATA_PATH)})...")
        stats = data_stats.compute()
        print(f"The staged build's data stats reconcile: {_records(stats)}")
        return

    print(f"Computing the data stats of the shipped data ({_relative(data_stats.DATA_PATH)})...")
    stats = data_stats.run()
    print(f"Wrote {_relative(data_stats.OUTPUT_PATH)}: {_records(stats)}")
    if not args.data_only:
        print(f"Measuring load time and memory per registry component ({args.runs} fresh-process runs per scenario)...")
        footprint.run(args.runs, args.notes)
        print(f"Wrote {_relative(footprint.OUTPUT_PATH)}")
        print(f"Benchmarking search ({args.sample_size:,} sampled entries per registry, {args.iterations} pass{'es' if args.iterations != 1 else ''} over each)...")
        benchmarks.run(args.sample_size, args.iterations, args.notes)
        print(f"Wrote {_relative(benchmarks.OUTPUT_PATH)}")
    updated = render_docs.render_all()
    print(f"Filled the stat markers in {', '.join(updated)}" if updated else "The docs' stat markers were already current")


if __name__ == "__main__":
    main()
