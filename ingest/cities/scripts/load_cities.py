from collections import Counter
from localis.utils.strings import is_latin
from ingest.utils import CITIES, ingest_log
from ingest.shared.models import SubdivisionModel, CountryModel, CityModel

# cities500.txt's columns, in order
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


def resolve_subdivision_chain(
    admin1: SubdivisionModel | None, admin2: SubdivisionModel | None
) -> list[SubdivisionModel]:
    """Walks the parent chain from the deepest resolved subdivision up to its root, ascending-admin_level ordered."""
    chain: list[SubdivisionModel] = []
    sub = admin2 or admin1
    while sub is not None:
        chain.append(sub)
        sub = sub.parent
    chain.reverse()
    return chain


def parse_row(
    row: dict[str, str],
    subdivisions: dict[str, SubdivisionModel],
    countries: dict[str, CountryModel],
) -> CityModel | None:
    """A city from one cities500 row, linked to its country and subdivision chain; None, logged, when its country isn't in this build."""
    geonames_id = row["geonameid"]

    # a name written in another script falls back to GeoNames' ASCII form
    name = row["name"] if is_latin(row["name"]) else row["asciiname"] or row["name"]
    if not is_latin(name):
        ingest_log.writeline(f"city {geonames_id} has no Latin name, so it ships as {name!r}", level="WARN")

    country_code, admin1_raw, admin2_raw = row["country code"], row["admin1 code"], row["admin2 code"]
    country = countries.get(country_code)
    if country is None:
        ingest_log.writeline(f"country not found: {country_code!r}, dropping city {name} ({geonames_id})", level="WARN")
        return None

    admin1 = subdivisions.get(f"{country_code}.{admin1_raw}")
    admin2 = subdivisions.get(f"{country_code}.{admin1_raw}.{admin2_raw}")
    return CityModel(
        geonames_id=int(geonames_id),
        name=name,
        subdivisions=resolve_subdivision_chain(admin1, admin2),
        country=country,
        population=int(row["population"] or 0),
        lat=float(row["latitude"]),
        lng=float(row["longitude"]),
    )


def load_cities(
    subdivisions: dict[str, SubdivisionModel], countries: dict[str, CountryModel]
) -> tuple[list[CityModel], dict[str, int]]:
    """The parsed cities, and the counts only parsing can see: the cities that took GeoNames' ASCII name over a primary name in another script, and the cities linked to no subdivision, by why."""
    ingest_log.writeline("Parsing cities from cities500.txt...")
    cities: list[CityModel] = []
    ascii_names = 0
    unlinked = {"no_admin1": 0, "admin1_00": 0, "unknown_admin1": 0}
    unknown_codes: Counter[str] = Counter()
    with open(CITIES.inputs / "cities500.txt", "r", encoding="utf-8") as f:
        for number, line in enumerate(f, start=1):
            # split on tabs rather than read as csv, which would take a field opening with a quote as quoted and run it into the rows after
            cells = line.rstrip("\r\n").split("\t")
            if len(cells) != len(HEADERS):
                raise ValueError(f"cities500.txt line {number} has {len(cells)} fields where GeoNames documents {len(HEADERS)}; check whether GeoNames changed the file's columns and update HEADERS in load_cities.py")
            row = dict(zip(HEADERS, cells))

            city = parse_row(row, subdivisions, countries)
            if city is None:
                continue
            cities.append(city)
            if city.name != row["name"]:
                ascii_names += 1
            # GeoNames leaves some places outside its admin1 divisions: no code, its "00", or a code its own admin1 file no longer lists (Singapore's retired districts)
            if not city.subdivisions:
                admin1_raw = row["admin1 code"]
                if not admin1_raw:
                    unlinked["no_admin1"] += 1
                elif admin1_raw == "00":
                    unlinked["admin1_00"] += 1
                else:
                    unlinked["unknown_admin1"] += 1
                    unknown_codes[f"{row['country code']}.{admin1_raw}"] += 1

    codes = ", ".join(f"{code} ({count})" for code, count in sorted(unknown_codes.items()))
    ingest_log.writeline(
        f"{sum(unlinked.values())} cities linked to no subdivision: {unlinked['no_admin1']} with no admin1 code, "
        f"{unlinked['admin1_00']} with GeoNames' 00, {unlinked['unknown_admin1']} with an admin1 code no subdivision carries{': ' + codes if codes else ''}"
    )
    return cities, {"ascii_names": ascii_names, **{f"unlinked_{reason}": count for reason, count in unlinked.items()}}
