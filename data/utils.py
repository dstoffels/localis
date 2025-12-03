from pathlib import Path
import json
import pickle
import gzip
from collections import defaultdict
from localis.models import Model, CountryModel, SubdivisionModel
from functools import partial

BASE_PATH = Path(__file__).parent
DATA_PATH = BASE_PATH.parent / "src" / "localis" / "data"
COUNTRIES_SRC_PATH = BASE_PATH / "countries" / "src"
SUB_SRC_PATH = BASE_PATH / "subdivisions" / "src"
CITIES_SRC_PATH = BASE_PATH / "cities" / "src"


def load_countries() -> dict[str, CountryModel]:
    ALPHA2_INDEX = 2
    print("Loading countries...")
    with gzip.open(DATA_PATH / "countries" / "countries.pkl.gz", "rb") as f:
        data: dict[int, list] = pickle.load(f)
        return {row[ALPHA2_INDEX]: CountryModel(*row) for row in data.values()}


def load_subdivisions() -> dict[str, SubdivisionModel]:
    print("Loading Subdivisions...")
    GEONAMES_CODE_INDEX = 1
    with gzip.open(DATA_PATH / "subdivisions" / "subdivisions.pkl.gz", "rb") as f:
        data: dict[int, list] = pickle.load(f)
        return {
            row[GEONAMES_CODE_INDEX]: SubdivisionModel(*row) for row in data.values()
        }


# def pkl_dump(data, file):
#     pickle.dump(data, file, protocol=pickle.HIGHEST_PROTOCOL)


def dump_data(data: list[Model], path: Path) -> None:
    cache: dict[int, tuple] = defaultdict(tuple)
    for item in data:
        cache[item.id] = item.to_row()
    with gzip.open(path, "wb", compresslevel=9) as f:
        # print(json.dumps(cache, indent=2))
        pickle.dump(cache, f, protocol=pickle.HIGHEST_PROTOCOL)


def dump_lookup_index(data: list[Model], path: Path) -> None:
    index: dict[str | int, int] = {}
    for item in data:
        for value in item.extract_lookup_values():
            index[value] = item.id
    with gzip.open(path, "wb", compresslevel=9) as f:
        # print(json.dumps(index, indent=2))
        pickle.dump(index, f, protocol=pickle.HIGHEST_PROTOCOL)


def dump_filter_index(data: list[Model], path: Path) -> None:
    index: dict[str, dict[str | int, list[int]]] = defaultdict(
        partial(defaultdict, list)
    )
    for item in data:
        filter_values = item.extract_filter_values()
        for filter_name, values in filter_values.items():
            for value in values:
                index[filter_name][value].append(item.id)

    # convert lists to tuples for immutability
    frozen_index = {
        fname: {val: tuple(ids) for val, ids in fdict.items()}
        for fname, fdict in index.items()
    }
    with gzip.open(path, "wb", compresslevel=9) as f:
        # print(json.dumps(index, indent=2))
        pickle.dump(frozen_index, f, protocol=pickle.HIGHEST_PROTOCOL)


def dump_search_index(data: list[Model], path: Path) -> None:
    index: dict[str, list[int]] = defaultdict(list)
    for item in data:
        for trigram in item.extract_search_trigrams():
            index[trigram].append(item.id)

    # convert lists to tuples for immutability
    frozen_index = {trigram: tuple(ids) for trigram, ids in index.items()}

    with gzip.open(path, "wb", compresslevel=9) as f:
        # print(json.dumps(index, indent=2))
        pickle.dump(frozen_index, f, protocol=pickle.HIGHEST_PROTOCOL)
