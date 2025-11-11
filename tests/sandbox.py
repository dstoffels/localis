from villager.db.models import CountryModel, CityModel, SubdivisionModel
import time

start = time.perf_counter()

for i in range(20):
    results = CityModel.fts_match("ma")

end = time.perf_counter()

print(f"Took {end - start:.6f} seconds")
