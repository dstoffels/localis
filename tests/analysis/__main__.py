import argparse
import sys
from tests.analysis import benchmarks, data_stats, footprint, render_docs


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="analysis",
        description="Runs the analysis suite: data stats, footprint and benchmarks, then fills the docs' stat markers.",
    )
    parser.add_argument("--data-only", action="store_true", help="only the deterministic data stats and docs, as CI runs after ingest")
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

    print("data stats...")
    data_stats.run()
    if not args.data_only:
        print("footprint...")
        footprint.run(args.runs, args.notes)
        print("benchmarks...")
        benchmarks.run(args.sample_size, args.iterations, args.notes)
    for doc in render_docs.render_all():
        print(f"updated {doc}")


if __name__ == "__main__":
    main()
