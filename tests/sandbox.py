import villager


results = villager.cities.search("madison al")

for r, s in results:
    print(r.json())
