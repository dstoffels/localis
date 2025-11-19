import villager
import time
from rapidfuzz import fuzz


start = time.perf_counter()
results = villager.subdivisions.types_for_country(alpha2="US")
end = time.perf_counter()

print(end - start)

for r in results:
    print(r)


# original, mangled = ["Musaffa|Musaffah City|Msfh", "Mskh"]

# score = fuzz.partial_token_sort_ratio(original, mangled)
# print(score)
