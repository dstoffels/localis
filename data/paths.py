from pathlib import Path

BASE_PATH = Path(__file__).parent

# localis data
DATA_PATH = BASE_PATH.parent / "src" / "localis" / "data"

# Raw
COUNTRIES_RAW_PATH = BASE_PATH / "countries" / "raw"
SUBDIVISIONS_RAW_PATH = BASE_PATH / "subdivisions" / "raw"
CITIES_RAW_PATH = BASE_PATH / "cities" / "raw"

# Manifest
COUNTRIES_MANIFEST_PATH = COUNTRIES_RAW_PATH / "countries.manifest.json"
SUBDIVISIONS_MANIFEST_PATH = SUBDIVISIONS_RAW_PATH / "subdivisions.manifest.json"
CITIES_MANIFEST_PATH = CITIES_RAW_PATH / "cities.manifest.json"

# Paths
GEONAMES_DUMP_URL = "https://download.geonames.org/export/dump"
