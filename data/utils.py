from pathlib import Path
import csv
from collections import defaultdict
from localis.models import Model, CountryModel, SubdivisionModel
import base64
import urllib.request

# Paths
BASE_PATH = Path(__file__).parent
DATA_PATH = BASE_PATH.parent / "src" / "localis" / "data"
COUNTRIES_RAW_PATH = BASE_PATH / "countries" / "raw"
SUBDIVISIONS_RAW_PATH = BASE_PATH / "subdivisions" / "raw"
CITIES_RAW_PATH = BASE_PATH / "cities" / "raw"

# Fetch URLs
USER_AGENT = "localis-data-refresh (+https://github.com/dstoffels/localis)"
GEONAMES_DUMP_URL = "https://download.geonames.org/export/dump"


def load_countries() -> dict[str, CountryModel]:
    ALPHA2_INDEX = 1
    print("Loading countries...")
    with open(DATA_PATH / "countries" / "countries.tsv", "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        return {
            row[ALPHA2_INDEX]: CountryModel(id, *row)
            for id, row in enumerate(reader, start=1)
        }


def load_subdivisions(
    countries: dict[str, CountryModel],
) -> dict[str, SubdivisionModel]:
    print("Loading Subdivisions...")
    GEONAMES_CODE_INDEX = 1
    COUNTRY_INDEX = 7
    countries_by_id: dict[int, CountryModel] = {c.id: c for c in countries.values()}
    with open(
        DATA_PATH / "subdivisions" / "subdivisions.tsv", "r", encoding="utf-8"
    ) as f:

        subdivisions: dict[str, SubdivisionModel] = {}
        reader = csv.reader(f, delimiter="\t")
        for id, row in enumerate(reader, start=1):
            country = countries_by_id.get(int(row[COUNTRY_INDEX]))
            row = row[:COUNTRY_INDEX] + ([country] if country else [])
            subdivisions[row[GEONAMES_CODE_INDEX]] = SubdivisionModel(id, *row)
        return subdivisions


def dump_data(data: list[Model], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        for item in data:
            writer.writerow(item.to_row())


def dump_lookup_index(data: list[Model], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        for item in data:
            row = []
            for value in item.extract_lookup_values():
                row.append(str(value))
            writer.writerow(["|".join(row)])


def dump_filter_index(data: list[Model], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        headers = data[0].FILTER_FIELDS.keys()
        writer.writerow(headers)
        for item in data:
            row = []
            for _, values in item.extract_filter_values().items():
                row.append("|".join([str(v) for v in values if v]))
            writer.writerow(row)


def _delta_encode(ids: list[int]) -> list[int]:
    ids.sort()
    out = []
    prev = 0
    for i in ids:
        out.append(i - prev)
        prev = i
    return out


def _varint_encode(value: int) -> bytes:
    out = bytearray()
    while True:
        b = value & 0x7F
        value >>= 7
        if value:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def encode_id_list(ids: set[int]) -> str:
    """Convert {1,5,6,...} → base64(varint(delta(ids)))"""
    deltas = _delta_encode(list(ids))

    # concat varints
    buf = bytearray()
    for d in deltas:
        buf.extend(_varint_encode(d))

    # Base64 encode for safe TSV storage
    return base64.b64encode(buf).decode("ascii")


def dump_search_index(data: list[Model], path: Path) -> None:
    index: dict[str, set[int]] = defaultdict(set)

    # Build posting lists
    for item in data:
        for trigram in item.extract_search_trigrams():
            index[trigram].add(item.id)

    # Write compressed format
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")

        for trigram, ids in index.items():
            encoded = encode_id_list(ids)
            writer.writerow([trigram, encoded])


def strip_comment_lines(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    path.write_text(
        "".join(l for l in lines if not l.startswith("#")), encoding="utf-8"
    )


def download(url: str, dest: Path) -> None:
    """Downloads url to dest, via a .part temp file so a failed transfer never leaves a corrupt file at dest."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response, open(tmp, "wb") as f:
        while chunk := response.read(1024 * 1024):
            f.write(chunk)

    tmp.replace(dest)
