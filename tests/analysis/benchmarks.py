import json
from datetime import datetime
import time
from localis.entities import Entity
from localis.registries import Registry
import localis
from tests.utils import mangle
import random

ITERATIONS = 50
SAMPLE_SIZE = 50

FAILURES_LOG_PATH = "tests/analysis/search_failures.log"


def benchmark():
    registries: list[str] = [
        "countries",
        "subdivisions",
        "cities",
    ]
    results: dict[str, object] = {
        "iterations": ITERATIONS,
        "sample_size": SAMPLE_SIZE,
    }
    results["notes"] = input("Notes: ")

    with open(FAILURES_LOG_PATH, "w") as log:
        log.write(f"# search failures - {datetime.now().isoformat()}\n")

        for registry_name in registries:
            print(f"Starting {registry_name}...")
            registry: Registry = getattr(localis, registry_name)
            entries: list[Entity] = list(registry)

            total_queries = 0
            num_hit = 0
            num_miss = 0
            avg_time = 0.0
            top_scores = []

            def search(q: str, entry: Entity, query_type: str):
                nonlocal total_queries, num_hit, num_miss, avg_time

                seed = hash((entry.id, i, query_type))
                mangled_q = mangle(q, seed=seed)
                start = time.perf_counter()
                search_results = registry.search(mangled_q)
                end = time.perf_counter()
                elapsed = (end - start) * 1000

                if total_queries == 0:
                    avg_time = elapsed
                else:
                    avg_time = (avg_time * total_queries + elapsed) / (
                        total_queries + 1
                    )

                total_queries += 1

                match_score = next(
                    (score for r, score in search_results if r.id == entry.id), None
                )
                if match_score is not None:
                    num_hit += 1
                    top_scores.append(match_score)
                else:
                    num_miss += 1
                    top = search_results[0] if search_results else None
                    top_desc = (
                        f'"{top[0].name}" ({top[1]:.2f})' if top else "no results"
                    )
                    log.write(
                        f'[{registry_name}:{query_type}] "{mangled_q}" -> expected "{q}" (id={entry.id}), got {top_desc}\n'
                    )

            # BEGIN SEARCHES
            for i in range(ITERATIONS):
                print(f"Pass {i + 1}")
                sample_rng = random.Random(i)
                sample_size = min(SAMPLE_SIZE, len(entries))
                sample = sample_rng.sample(entries, sample_size)

                for entry in sample:
                    q = entry.name
                    if isinstance(entry, localis.City) and entry.admin1:
                        q += f" {entry.admin1.name}"
                    search(q, entry, "name")

                    aliases = getattr(entry, "aliases", None)
                    if aliases:
                        alias_rng = random.Random(hash((entry.id, i)))
                        alias = alias_rng.choice(aliases)
                        search(alias, entry, "alias")

            success_rate = num_hit / total_queries if total_queries else 0.0
            avg_hit_score = sum(top_scores) / num_hit if num_hit else 0.0

            results[registry_name] = {
                "queries": total_queries,
                "failures": num_miss,
                "success_rate": round(success_rate, 3),
                "avg_time_ms": round(avg_time, 3),
                "avg_hit_score": round(avg_hit_score, 3),
            }

    return results


def write_file(results: dict[str, object]):

    file_path = "tests/analysis/search_benchmarks.json"
    now_key = datetime.now().isoformat()

    # load existing data if file exists
    try:
        with open(file_path, "r") as f:
            all_results = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        all_results = {}

    # add the new benchmark under the current datetime key
    all_results[now_key] = results

    # write back the updated object
    with open(file_path, "w") as f:
        json.dump(all_results, f, indent=4)


def main():
    results = benchmark()
    print(json.dumps(results, indent=4))
    results["report"] = input("Report: ")
    write_file(results)


if __name__ == "__main__":
    main()
