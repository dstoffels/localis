from pathlib import Path
import csv
import json

BASE_PATH = Path(__file__).parent

HEADERS = [
    "geonameid",
    "name",
    "asciiname",
    "alternatenames",
    "latitude",
    "longitude",
    "feature class",
    "feature code",
    "country code",
    "cc2",
    "admin1 code",
    "admin2 code",
    "admin3 code",
    "admin4 code",
    "population",
    "elevation",
    "dem",
    "timezone",
    "modification date",
]

with open(BASE_PATH / "cities" / "src" / "allCountries.txt", encoding="utf-8") as f:

    all = csv.DictReader(f, delimiter="\t", fieldnames=HEADERS)
    for row in all:
        if row["name"] == "Madison" and row["admin1 code"] == "WI":
            print(json.dumps(row, indent=4))
            break
