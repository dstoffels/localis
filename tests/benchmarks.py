import json
from datetime import datetime
import time
from villager.dtos import DTO
from villager.registries import Registry
import villager
from tests.utils import mangle

ITERATIONS = 3
SAMPLE_SIZE = 300


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
        registry: Registry = getattr(villager, registry_name)
        entries: list[DTO] = list(registry)

        total_queries = 0
        num_hit = 0
        num_miss = 0
        avg_time = 0.0
        top_scores = []

        for i in range(ITERATIONS):
            print(f"Pass {i}")
            for entry in entries[:SAMPLE_SIZE]:
                seed = hash((entry.id, i))
                query = mangle(entry.name, seed=seed)
                start = time.perf_counter()
                search_results = registry.search(query, limit=10)
                end = time.perf_counter()
                elapsed = (end - start) * 1000
                # avg_entry_score = not len(search_results) or sum(
                #     [score for _, score in search_results]
                # ) / len(search_results)

                if total_queries == 0:
                    avg_time = elapsed
                    # avg_top_score = avg_entry_score
                else:
                    avg_time = (avg_time * total_queries + elapsed) / (
                        total_queries + 1
                    )

                    # avg_top_score = (avg_top_score * total_queries + avg_entry_score) / (
                    #     total_queries + 1
                    # )

                total_queries += 1

                for r, score in search_results:
                    if entry.id == r.id:
                        num_hit += 1
                        top_scores.append(score)
                    else:
                        num_miss += 1
        success_rate = num_hit / total_queries if total_queries else 0.0
        avg_hit_score = sum(top_scores) / num_hit

        results[registry_name] = {
            "success_rate": round(success_rate, 3),
            "avg_time_ms": round(avg_time, 3),
            "avg_hit_score": round(avg_hit_score, 3),
        }
    return results


def write_file(results: dict):

    file_path = "tests/search_benchmarks.json"
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
