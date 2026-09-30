from ingest.utils import COUNTRIES_RAW_PATH
import json
from ingest.countries import CountryModel


def is_valid_name(alias: str, country: CountryModel):
    if "ISO 3166" in alias:
        return False

    if len(alias) <= 3:
        return False

    if alias.lower().strip() in [
        country.alpha2.lower(),
        country.alpha3.lower(),
        country.name.lower(),
        country.official_name.lower(),
        country.numeric.__str__().lower(),
    ]:
        return False
    return True


def merge_wikidata(countries: dict[str, CountryModel]):
    with open(COUNTRIES_RAW_PATH / "wiki_countries.json", "r", encoding="utf-8") as f:
        wiki_countries: list[dict[str, str]] = json.load(f)

        for row in wiki_countries:
            alpha2: str = row["alpha2"]

            country: CountryModel = countries.get(alpha2, None)

            if not country:
                continue

            # merge name
            name: str = row.get("name", "")
            if name and name.lower() not in [n.lower() for n in country.aliases]:
                country.aliases.append(name)

            # merge validated alt names
            aliases: list[str] = row.get("aliases", "").split("|")
            for a in aliases:
                if is_valid_name(a, country):
                    country.aliases.append(a)


def merge_geonames(countries: dict[str, CountryModel]):
    with open(
        COUNTRIES_RAW_PATH / "geonames_countries.txt", "r", encoding="utf-8"
    ) as f:

        for row in f:
            parts = row.strip().split("\t")
            alpha2 = parts[0]
            alpha3 = parts[1]
            numeric = parts[2]
            name = parts[4]

            country: CountryModel = countries.get(alpha2)

            if not country:
                country = CountryModel(
                    id=len(countries) + 1,
                    alpha2=alpha2,
                    alpha3=alpha3,
                    numeric=int(numeric),
                    name=name,
                    official_name="",
                    aliases=[],
                    flag=None,
                )
                countries[alpha2] = country

            # add name if not duplicate
            if name and name.lower() not in [
                country.name.lower(),
                country.official_name.lower(),
                *[n.lower() for n in country.aliases],
            ]:
                country.aliases.append(name)

            # remove name/official name from aliases if present
            if country.name in country.aliases:
                country.aliases.remove(country.name)
            if country.official_name in country.aliases:
                country.aliases.remove(country.official_name)
