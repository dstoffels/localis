import villager
from rapidfuzz import process, fuzz
import time


# dtos = villager.localities

# duration = 0.0
# for c in dtos:
#     start = time.perf_counter()
#     results = villager.localities.search(c.name)
#     results = [r.name for r in results]
#     duration += time.perf_counter() - start

# print(f"Duration: {duration:.3f}s")

tokens = ["carbondale"]

for step in range(10):
    print(step)

    new_tokens = []
    for t in tokens:
        new_len = max(2, len(t) - step)
        new_tokens.append(t[:new_len])

        print(new_tokens)
