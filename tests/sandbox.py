import villager
import time

q, name = ["Btaziliano", "Braziliano"]

start = time.perf_counter()
results = villager.cities.search("madson wi", limit=10)
end = time.perf_counter()

print((end - start) / 1000)

for r, score in results:
    print(r.display_name, score)


# from rapidfuzz import fuzz

# score = fuzz.token_set_ratio(q, name)
# print(score / 100)
