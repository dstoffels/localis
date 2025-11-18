import villager
import time
from rapidfuzz import fuzz


start = time.perf_counter()
results = villager.cities.search("Palo Gcho", limit=10)
end = time.perf_counter()

print(end - start)

for r, score in results:
    print(r.display_name, score)


original, mangled = ["Bodr\u012b", "Bdor\u012b"]

score = fuzz.token_sort_ratio(original, mangled)
print(score)
