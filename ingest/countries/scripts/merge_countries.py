import json
import re
import unicodedata
from ingest.utils import COUNTRIES, ingest_log
from ingest.utils.strings import name_key
from localis.utils.strings import is_latin
from ingest.shared.models import CountryModel
from .fetch_countries import GEONAMES_COUNTRIES_DEST
from .load_historic_countries import historic_by_alpha2
from .wikidata_countries import CountryNames

_LEADING_THE_RE = re.compile(r"^the\s+", re.IGNORECASE)
_SUBDIVISION_CODE_RE = re.compile(r"^[A-Z]{2}-[A-Z0-9]{1,3}$")
NAME_BLOCKLIST_PATH = COUNTRIES.inputs / "name_blocklist.json"


def _wikidata_alias(raw: str, iso_codes: set[str], item_codes: frozenset[str] | set[str] = frozenset()) -> str | None:
    """The alias a Wikidata name contributes, or None if it isn't a usable name."""
    alias = _LEADING_THE_RE.sub("", " ".join(raw.split()))
    # digits, slashes and symbols mark identifiers rather than names: "ISO 3166-1:BH", "+256", "Atlantic/Faroe", flag emoji
    if not alias or any(ch.isdigit() or ch == "/" or unicodedata.category(ch).startswith("S") for ch in alias):
        return None
    # the item's own IOC/FIFA codes and ISO 3166-2-shaped codes ("GB-GSY", "US-GU") are codes, not names
    if alias in item_codes or _SUBDIVISION_CODE_RE.match(alias):
        return None
    # the query asks for English, so a letter outside Latin script marks a mislabelled name (Armenian, Cyrillic, Greek)
    if not is_latin(alias):
        return None
    # a short entry is kept only as an uppercase abbreviation that isn't itself an ISO code: "UK", "DRC" and "ROC" stay; language and domain codes ("el", "zaf") and ISO codes ("CAN", "TWN") go
    if len(alias) <= 3 and not (alias.isalpha() and alias.isupper() and alias not in iso_codes):
        return None
    return alias


def _load_blocklist() -> dict[str, dict[str, str]]:
    """Names that pass the filters but aren't names of the country (nicknames, demonyms, misspellings, stray codes), by name_key() under alpha-2, or alpha-4 for a historic entry; each entry's reason is recorded in the file."""
    blocklist: dict[str, dict[str, str]] = json.loads(NAME_BLOCKLIST_PATH.read_text(encoding="utf-8"))
    return {code: {name_key(name): name for name in names} for code, names in blocklist.items()}


def merge_wikidata(countries: dict[str, CountryModel], country_names: CountryNames) -> None:
    """Adds each country's Wikidata names as aliases, matched by the key it's stored under: alpha-2 for a current country, alpha-4 for a historic one."""
    ingest_log.writeline("Merging Wikidata country names...")
    iso_codes = {code for c in countries.values() for code in (c.alpha2, c.alpha3) if code}
    blocklist = _load_blocklist()
    used: set[tuple[str, str]] = set()

    for code, entry in country_names.items():
        country = countries.get(code)
        if country is None:
            continue
        blocked = blocklist.get(code, {})
        item_codes = set(entry["codes"])
        # a short name is exempt from the item's sports codes, which some abbreviations share (UAE, RSA), but not from ISO codes, most of which are the country's own (NG, MYS)
        aliases = [_wikidata_alias(name, iso_codes, item_codes) for name in entry["names"]]
        aliases += [_wikidata_alias(name, iso_codes) for name in entry["short_names"]]
        for alias in aliases:
            if not alias:
                continue
            if name_key(alias) in blocked:
                used.add((code, name_key(alias)))
                continue
            country.aliases.append(alias)

    stale = [f"{code} {name!r}" for code, names in blocklist.items() for key, name in names.items() if (code, key) not in used]
    if stale:
        ingest_log.writeline(f"blocklist entries that no longer block a Wikidata name, safe to remove from name_blocklist.json: {', '.join(stale)}", level="WARN")


def drop_ambiguous_aliases(countries: dict[str, CountryModel]) -> None:
    """Removes a current country's alias when another current country has it as a name or alias, so it can't resolve to the wrong country."""
    current = [c for c in countries.values() if not c.historic]
    owners: dict[str, set[str]] = {}
    for c in current:
        for name in (c.name, c.official_name, c.common_name, *c.aliases):
            if name:
                owners.setdefault(name_key(name), set()).add(c.alpha2)
    for c in current:
        ambiguous = [a for a in c.aliases if len(owners[name_key(a)]) > 1]
        if ambiguous:
            ingest_log.writeline(f"{c.alpha2}: dropped aliases shared with another country: {', '.join(sorted(ambiguous))}")
            c.aliases = [a for a in c.aliases if a not in ambiguous]


# GeoNames countries file format: tab-separated values with the following columns:
# ISO	ISO3	ISO-Numeric	fips	Country	Capital	Area(in sq km)	Population	Continent	tld	CurrencyCode	CurrencyName	Phone	Postal Code Format	Postal Code Regex	Languages	geonameid	neighbours	EquivalentFipsCode
def merge_geonames(countries: dict[str, CountryModel]) -> None:
    """Sets each country's GeoNames id and adds GeoNames' name as an alias, adding a country GeoNames lists under a code in neither ISO list (Kosovo)."""
    ingest_log.writeline("Merging GeoNames countries...")

    # historic entries are keyed by alpha_4, so a GeoNames row for a withdrawn code (CS, AN) would otherwise be added as a new country; a code ISO reused goes to its most recent holder, the country GeoNames still lists under it (CS: Serbia and Montenegro, not Czechoslovakia)
    historic_entries = historic_by_alpha2(countries)

    with open(GEONAMES_COUNTRIES_DEST, "r", encoding="utf-8") as f:

        for row in f:
            # GeoNames ships this with a '#' doc header, read past rather than stripped, so the input stays the file the manifest hashes
            if row.startswith("#"):
                continue
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

            country: CountryModel | None = countries.get(alpha2) or next(reversed(historic_entries.get(alpha2, [])), None)

            # Construct new country
            if not country:
                ingest_log.writeline(
                    f"country not in ISO 3166-1, added from GeoNames: {alpha2} ({name})"
                )
                country = CountryModel(
                    alpha2=alpha2,
                    alpha3=alpha3,
                    geonames_id=geonames_id,
                    numeric=int(numeric) or None,
                    name=name,
                    official_name=None,
                    common_name=None,
                    aliases=[],
                    flag=None,
                    historic=None,
                )
                countries[alpha2] = country

            country.geonames_id = geonames_id
            # ingest_countries() dedupes every alias against the country's names once all sources are merged
            if name:
                country.aliases.append(name)
