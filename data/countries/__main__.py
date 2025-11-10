# This script aggregates country data primarily from ISO 3166-1, supplemented with Wikidata and GeoNames for aliases and search tokens.
# We do not use geonames alternateNames.txt as they're noisy and mainly historical.

from pathlib import Path
import csv
import re
import json


BASE_PATH = Path(__file__).parent

from dataclasses import dataclass, field


# helper dto class
@dataclass
class CountryDTO:
    alpha2: str
    alpha3: str
    numeric: int
    name: str
    official_name: str
    aliases: list[str] = field(default_factory=list)
    names: list[str] = field(default_factory=list)
    geonames_id: str = ""
    qid: str = ""
    fips: str = ""
    flag: str = ""


countries: dict[str, CountryDTO] = {}


def init_iso_countries():
    # contemporary name mappings
    NAME_MAP = {
        "CG": "Republic of the Congo",
        "CD": "Democratic Republic of the Congo",
        "FK": "Falkland Islands",
        "FM": "Micronesia",
        "MF": "Saint-Martin",
        "SX": "Sint Maarten",
        "PS": "Palestine",
        "SH": "Saint Helena",
        "VA": "Holy See",
        "VG": "British Virgin Islands",
        "VI": "U.S. Virgin Islands",
        "VN": "Viet Nam",
    }

    OFF_NAME_MAP = {
        "FK": "Falkland Islands (Malvinas)",
        "KR": "Republic of Korea",
        "LA": "Lao People's Democratic Republic",
        "MF": "Collectivity of Saint Martin",
        "SX": "Country of Sint Maarten",
        "SH": "Saint Helena, Ascension and Tristan da Cunha",
        "SY": "Syrian Arab Republic",
        "TW": "Republic of China",
        "VA": "Vatican City State",
    }

    with open(BASE_PATH / "src/iso3166-1.json", "r", encoding="utf-8") as f:
        iso_countries = json.load(f).get("3166-1")
        iso_countries.sort(key=lambda c: c.get("alpha_2"))

        for row in iso_countries:
            name = (
                NAME_MAP.get(row["alpha_2"])
                or row.get("common_name")
                or row.get("name")
            )
            official_name = (
                OFF_NAME_MAP.get(row["alpha_2"]) or row.get("official_name") or name
            )

            country = CountryDTO(
                alpha2=row["alpha_2"],
                alpha3=row["alpha_3"],
                numeric=int(row["numeric"]),
                name=name,
                official_name=official_name,
                flag=row["flag"],
            )
            countries[country.alpha2] = country


def merge_wikidata():
    with open(BASE_PATH / "src/wiki_countries.json", "r", encoding="utf-8") as f:
        wiki_countries = json.load(f)
        for row in wiki_countries:
            if row.get("alpha3"):
                alpha2 = row["alpha2"]
                if alpha2 not in countries:
                    countries[alpha2] = CountryDTO(
                        alpha2=alpha2,
                        alpha3=row.get("alpha3", ""),
                        name=row.get("name", ""),
                        numeric=None,
                    )

                country: CountryDTO = countries.get(row["alpha2"])
                country.qid = row.get("qid", "")

                name = row.get("name", "")
                if name and name not in country.names:
                    country.names.append(name)

                names: list[str] = row.get("aliases", "").split("|")
                country.names.extend(names)


def merge_geonames():
    with open(BASE_PATH / "src/geonames_countries.txt", "r", encoding="utf-8") as f:
        # #ISO	ISO3	ISO-Numeric	fips	Country	Capital	Area(in sq km)	Population	Continent	tld	CurrencyCode CurrencyName	Phone	Postal Code Format	Postal Code Regex	Languages	geonameid	neighbours	EquivalentFipsCode

        for line in f:
            parts = line.strip().split("\t")
            alpha2 = parts[0]
            alpha3 = parts[1]
            fips = parts[3]
            name = parts[4]
            geonames_id = parts[16]

            country: CountryDTO = countries.get(alpha2)
            if not country:
                continue

            country.alpha3 = alpha3
            country.fips = fips
            country.geonames_id = geonames_id

            if name and name not in country.names:
                country.names.append(name)


def clean_tokens():
    for country in countries.values():

        # initial deduplication
        country.names = list(set(country.names))

        country_names = [name for name in country.names]
        for name in country_names:
            name_lower = name.lower()
            if (
                "ISO 3166" in name
                or name_lower == country.alpha2.lower()
                or name_lower == country.alpha3.lower()
                or name_lower == country.name.lower()
                or name_lower == country.official_name.lower()
                or name_lower == country.numeric.__str__().lower()
                or name_lower == country.fips.lower()
                or any(n.lower() == name_lower for n in country.names if n != name)
            ):
                country.names.remove(name)


def parse_tokens(names: list[str], name: str) -> str:
    TOKEN_SPLIT_RE = re.compile(r"[\W_]+")
    STOPWORDS = {"the", "of", "and"}

    tokens: set[str] = set()

    for n in names:
        parts = TOKEN_SPLIT_RE.split(n.lower().strip())
        for p in parts:
            if p not in name.lower().split() and p not in STOPWORDS and len(p) > 2:
                tokens.add(p)

    return " ".join(sorted(tokens))


def build_row(country: CountryDTO) -> list[str]:
    ALIAS_MAP = {
        "GB": [
            "Great Britain",
            "Britain",
            "UK",
            "England",
            "Scotland",
            "Wales",
            "Northern Ireland",
        ],
        "US": ["America"],
        "CI": ["Ivory Coast", "Cote d'Ivoire"],
        "MM": ["Burma"],
        "SZ": ["Swaziland"],
        "NL": ["Holland"],
        "MK": ["Macedonia"],
        "CV": ["Cape Verde"],
        "SY": ["Syria"],
        "RU": ["Russia", "USSR", "Soviet Union"],
        "VN": ["Vietnam"],
        "CG": ["Congo-Brazzaville", "Congo Republic"],
        "CD": ["DRC", "Congo-Kinshasa", "DR Congo", "Zaire"],
        "BN": ["Brunei"],
        "ST": ["São Tomé and Príncipe"],
        "TL": ["East Timor"],
        "RS": ["Yugoslavia"],
        "BQ": ["Netherlands Antilles", "Dutch Antilles", "Carribean Netherlands"],
        "SX": ["Land Sint Maarten", "Dutch Sint Maarten"],
        "MF": ["Collectivité de Saint-Martin"],
        "TW": ["ROC"],
    }

    return [
        country.geonames_id,
        country.name,
        country.official_name,
        country.alpha2,
        country.alpha3,
        country.numeric,
        country.flag,
        "|".join(ALIAS_MAP.get(country.alpha2, [])),
        parse_tokens(country.names, country.name),
    ]


def print_to_tsv():
    headers = (
        "id",
        "name",
        "official_name",
        "alpha2",
        "alpha3",
        "numeric",
        "flag",
        "aliases",
        "tokens",
    )
    rows: list[list[str]] = [build_row(c) for c in countries.values()]

    with open(BASE_PATH / "countries.tsv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)


def main():
    init_iso_countries()
    merge_wikidata()
    merge_geonames()
    clean_tokens()
    print_to_tsv()


if __name__ == "__main__":
    main()
