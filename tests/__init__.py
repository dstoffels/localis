import localis
from rapidfuzz import fuzz

results = localis.cities.search("Bezuchov")

# for r, s in results:
# print(r.name, s)

score = fuzz.token_set_ratio("Hulu", "Hulh")
print(score)
