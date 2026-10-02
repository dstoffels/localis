from ingest.utils import COUNTRIES_INPUTS_PATH, ingest_log
import json
from ingest.shared.models import CountryModel
from .fetch_countries import GEONAMES_COUNTRIES_DEST


def is_valid_name(alias: str, country: CountryModel):
    if "ISO 3166" in alias:
        return False

    if len(alias) <= 3:
        return False

    if alias.lower().strip() in [
        country.alpha2.lower(),
        (country.alpha3 or "").lower(),
        country.name.lower(),
        country.official_name.lower(),
        str(country.numeric).lower(),
    ]:
        return False
    return True


def merge_wikidata(countries: dict[str, CountryModel]):
    ingest_log.writeline("Merging Wikidata aliases...")
    with open(
        COUNTRIES_INPUTS_PATH / "wiki_countries.json", "r", encoding="utf-8"
    ) as f:
        wiki_countries: list[dict[str, str]] = json.load(f)

        for row in wiki_countries:
            alpha2: str = row["alpha2"]

            country: CountryModel | None = countries.get(alpha2, None)

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


# GeoNames countries file format: tab-separated values with the following columns:
# ISO	ISO3	ISO-Numeric	fips	Country	Capital	Area(in sq km)	Population	Continent	tld	CurrencyCode	CurrencyName	Phone	Postal Code Format	Postal Code Regex	Languages	geonameid	neighbours	EquivalentFipsCode
def merge_geonames(countries: dict[str, CountryModel]):
    ingest_log.writeline("Merging GeoNames countries...")

    # historic entries are keyed by alpha_4, not alpha2, so a plain countries.get(alpha2)
    # misses them; without this, a GeoNames row for a historic country (e.g. CS) would
    # fall through to "construct new country" and duplicate the entry already loaded from ISO 3166-3
    historic_by_alpha2 = {c.alpha2: c for c in countries.values() if c.historic}

    with open(GEONAMES_COUNTRIES_DEST, "r", encoding="utf-8") as f:

        for row in f:
            (
                alpha2,
                alpha3,
                numeric,
                fips,
                name,
                capital,
                area,
                population,
                continent,
                tld,
                currency_code,
                currency_name,
                phone,
                postal_code_format,
                postal_code_regex,
                languages,
                geonames_id,
                neighbours,
                equivalent_fips_code,
            ) = row.rstrip("\r\n").split("\t")

            geonames_id = int(geonames_id)

            country: CountryModel | None = countries.get(alpha2) or historic_by_alpha2.get(alpha2)

            # Construct new country
            if not country:
                ingest_log.writeline(
                    f"country not in ISO 3166-1, added from GeoNames: {alpha2} ({name})"
                )
                country = CountryModel(
                    id=len(countries) + 1,
                    alpha2=alpha2,
                    alpha3=alpha3,
                    geonames_id=geonames_id,
                    numeric=int(numeric),
                    name=name,
                    official_name="",
                    aliases=[],
                    flag=None,
                    historic=None,
                )
                countries[alpha2] = country

            # Merge GeoNames data into existing ISO country
            country.geonames_id = geonames_id

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
