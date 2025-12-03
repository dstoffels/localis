from pathlib import Path
import json
import gzip
from collections import defaultdict
from localis.models import Model, CountryModel, SubdivisionModel

BASE_PATH = Path(__file__).parent
DATA_PATH = BASE_PATH.parent / "src" / "localis" / "data"
COUNTRIES_SRC_PATH = BASE_PATH / "countries" / "src"
SUB_SRC_PATH = BASE_PATH / "subdivisions" / "src"
CITIES_SRC_PATH = BASE_PATH / "cities" / "src"


def load_countries() -> dict[str, CountryModel]:
    ALPHA2_INDEX = 2
    print("Loading countries...")
    with gzip.open(
        DATA_PATH / "countries" / "countries.json.gz", "rt", encoding="utf-8"
    ) as f:
        data: dict[int, list] = json.load(f)
        return {row[ALPHA2_INDEX]: CountryModel(*row) for row in data.values()}


def load_subdivisions() -> dict[str, SubdivisionModel]:
    print("Loading Subdivisions...")
    GEONAMES_CODE_INDEX = 1
    with gzip.open(
        DATA_PATH / "subdivisions" / "subdivisions.json.gz", "rt", encoding="utf-8"
    ) as f:
        data: dict[int, list] = json.load(f)
        return {
            row[GEONAMES_CODE_INDEX]: SubdivisionModel(*row) for row in data.values()
        }


def json_dump(data, file):
    json.dump(data, file, ensure_ascii=False, indent=2, separators=(",", ": "))


def dump_data(data: list[Model], path: Path) -> None:
    cache: dict[int, list] = defaultdict(list)
    for item in data:
        cache[item.id] = item.to_row()
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=9) as f:
        # print(json.dumps(cache, indent=2))
        json_dump(cache, f)


def dump_lookup_index(data: list[Model], path: Path) -> None:
    index: dict[str | int, int] = {}
    for item in data:
        for value in item.extract_lookup_values():
            index[value] = item.id
    with gzip.open(path, "wt", compresslevel=9) as f:
        # print(json.dumps(index, indent=2))
        json_dump(index, f)


def dump_filter_index(data: list[Model], path: Path) -> None:
    index: dict[str, dict[str | int, list[int]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for item in data:
        filter_values = item.extract_filter_values()
        for filter_name, values in filter_values.items():
            for value in values:
                index[filter_name][value].append(item.id)
    with gzip.open(path, "wt", compresslevel=9) as f:
        # print(json.dumps(index, indent=2))
        json_dump(index, f)


def dump_search_index(data: list[Model], path: Path) -> None:
    index: dict[str, list[int]] = defaultdict(list)
    for item in data:
        for trigram in item.extract_search_trigrams():
            index[trigram].append(item.id)
    with gzip.open(path, "wt", compresslevel=9) as f:
        # print(json.dumps(index, indent=2))
        json_dump(index, f)
