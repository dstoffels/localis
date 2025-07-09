from villager.registries import CountryRegistry, SubdivisionRegistry, LocalityRegistry
from villager.db import CountryModel, SubdivisionModel, LocalityModel
from villager.types import Country, Subdivision, Locality

countries = CountryRegistry(CountryModel, Country)
subdivisions = SubdivisionRegistry(SubdivisionModel, Subdivision)
localities = LocalityRegistry(LocalityModel, Locality)

# from peewee import fn


# def search_countries_by_trigram(query: str, threshold: float = 0.3):
#     similarity_expr = fn.trigram_sim(CountryModel.normalized_name, query)
#     q = (
#         CountryModel.select(
#             CountryModel.id, CountryModel.name, similarity_expr.alias("similarity")
#         )
#         .where(similarity_expr > threshold)
#         .order_by(similarity_expr.desc())
#         .limit(5)
#     )
#     print(q.sql())
#     return q


# if __name__ == "__main__":
#     results = list(search_countries_by_trigram("untied stants"))
#     for country in results:
#         print(country.name, getattr(country, "similarity"))
