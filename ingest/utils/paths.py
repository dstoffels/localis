from pathlib import Path

BASE_PATH = Path(__file__).parent.parent

# localis data
DATA_PATH = BASE_PATH.parent / "src" / "localis" / "data"

# Published docs
DOCS_PATH = BASE_PATH.parent / "docs"

# Inputs (fetched sources only)
COUNTRIES_INPUTS_PATH = BASE_PATH / "countries" / "inputs"
SUBDIVISIONS_INPUTS_PATH = BASE_PATH / "subdivisions" / "inputs"
CITIES_INPUTS_PATH = BASE_PATH / "cities" / "inputs"
SHARED_INPUTS_PATH = BASE_PATH / "shared" / "inputs"

# Outputs (ingestion-process artifacts: resolution decisions, orphan lists, not raw input)
COUNTRIES_OUTPUTS_PATH = BASE_PATH / "countries" / "outputs"
SUBDIVISIONS_OUTPUTS_PATH = BASE_PATH / "subdivisions" / "outputs"
CITIES_OUTPUTS_PATH = BASE_PATH / "cities" / "outputs"

# Logs
COUNTRIES_LOGS_PATH = BASE_PATH / "countries" / "logs"
SUBDIVISIONS_LOGS_PATH = BASE_PATH / "subdivisions" / "logs"
CITIES_LOGS_PATH = BASE_PATH / "cities" / "logs"

# Manifest
COUNTRIES_MANIFEST_PATH = COUNTRIES_INPUTS_PATH / "countries.manifest.json"
SUBDIVISIONS_MANIFEST_PATH = SUBDIVISIONS_INPUTS_PATH / "subdivisions.manifest.json"
CITIES_MANIFEST_PATH = CITIES_INPUTS_PATH / "cities.manifest.json"
SHARED_MANIFEST_PATH = SHARED_INPUTS_PATH / "shared.manifest.json"

# Paths
GEONAMES_DUMP_URL = "https://download.geonames.org/export/dump"
