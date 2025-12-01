import json
from datetime import datetime
import time
from localis.data.model import DTO
from localis.registries import Registry
import localis
from tests.utils import mangle
import random

ITERATIONS = 1
SAMPLE_SIZE = 1000


def benchmark():
    registries: list[str] = [
        "countries",
        "subdivisions",
        "cities",
    ]
    results: dict[str, str | set] = {
        "iterations": ITERATIONS,
        "sample_size": SAMPLE_SIZE,
    }
    results["notes"] = input("Notes: ")

    for registry_name in registries:
        print(f"Starting {registry_name}...")
        registry: Registry = getattr(localis, registry_name)
        entries: list[DTO] = list(registry)

        total_queries = 0
        num_hit = 0
        num_miss = 0
        avg_time = 0.0
        top_scores = []

        def search(q: str):
            nonlocal total_queries, num_hit, num_miss, avg_time

            seed = hash((entry.id, i))
            mangled_q = mangle(q, seed=seed)
            start = time.perf_counter()
            search_results = registry.search(mangled_q)
            end = time.perf_counter()
            elapsed = (end - start) * 1000

            if total_queries == 0:
                avg_time = elapsed
            else:
                avg_time = (avg_time * total_queries + elapsed) / (total_queries + 1)

            total_queries += 1

            for r, score in search_results:
                if entry.id == r.id:
                    num_hit += 1
                    top_scores.append(score)
                else:
                    num_miss += 1

        # BEGIN SEARCHES
        for i in range(ITERATIONS):
            print(f"Pass {i + 1}")
            for entry in entries[:SAMPLE_SIZE]:
                q = entry.name
                if hasattr(entry, "admin1") and entry.admin1:
                    q += f" {entry.admin1.name}"
                search(q)
                # if entry.aliases:
                #     rand_alt_name = random.Random(42 + i).choice(entry.alt_names)
                #     search(rand_alt_name)

        success_rate = num_hit / total_queries if total_queries else 0.0
        avg_hit_score = sum(top_scores) / num_hit

        results[registry_name] = {
            "success_rate": round(success_rate, 3),
            "avg_time_ms": round(avg_time, 3),
            "avg_hit_score": round(avg_hit_score, 3),
        }
    return results


def write_file(results: dict):

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
