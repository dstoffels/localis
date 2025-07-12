import villager
from rapidfuzz import fuzz
import time

start = time.perf_counter()

res = villager.countries.search("  meco")

duration = time.perf_counter() - start

print([(r.name, r.alpha2, s) for r, s in res])
print(f"Duration: {duration:.3f}s")
