from villager.db.models import CountryModel, CityModel, SubdivisionModel
import time

query = "san fran"

start = time.perf_counter()
for i in range(100):
    results = CityModel.fts_match("milwaukee", order_by=["population desc"])
end = time.perf_counter()

for r in results:
    print(r)


print(f"Took {round((end - start) * 1000,2)}ms")
