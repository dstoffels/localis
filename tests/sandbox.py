# import villager

# # import pycountry

# # for s in pycountry.subdivisions:
# #     print(s)

# results = villager.cities.search("ஹராரே")


# for r in results:
#     print(r)
#     print()


from rapidfuzz import fuzz

print(fuzz.token_set_ratio("Gur", "Gor"))
