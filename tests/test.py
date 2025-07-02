import piecountry

print([(c.name, ratio) for c, ratio in piecountry.countries.search("cananda")])
print(piecountry.countries.get(4).name)
print(piecountry.subdivisions.get_types("GB"))
print(piecountry.countries.get("uk").name)
