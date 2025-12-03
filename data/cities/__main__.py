# This script parses geonames' allCountries.txt into a filtered TSV of cities with enriched data for country, subdivision and alternate city names as search tokens.
# Country and subdivision data are loaded from separate TSV files.
# Cities are filtered based on feature codes and population. We only want to include actual populated settlements as allCountries.txt contains many other geographical features.
# allCountries.txt (1.64GB) must be manually downloaded to the src folder from https://download.geonames.org/export/dump/

from data.cities.scripts.utils import *
from data.cities.scripts.load import load_cities
from data.cities.scripts.dump import dump
from data.utils import *
from localis.models import SubdivisionModel, CountryModel, CityModel


def main():
    countries: dict[str, CountryModel] = (
        load_countries()
    )  # map of country codes to CountryModel
    subdivisions: dict[str, SubdivisionModel] = (
        load_subdivisions()
    )  # map of subdivision geonames codes to SubdivisionModel
    cities: list[CityModel] = load_cities(
        subdivisions, countries
    )  # load and parse cities
    dump(cities)


if __name__ == "__main__":
    main()
