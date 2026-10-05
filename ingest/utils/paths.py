from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent.parent
REPO_PATH = BASE_PATH.parent

# localis data
DATA_PATH = REPO_PATH / "src" / "localis" / "data"

# Published docs
DOCS_PATH = REPO_PATH / "docs"

# Each run's build, promoted to the repo only once every stage has dumped and the reconcile gate passes
STAGING_PATH = BASE_PATH / "staging"
STAGED_DATA_PATH = STAGING_PATH / "data"

# each run's steps and result, however it ends
PIPELINE_LOG_PATH = BASE_PATH / "pipeline.log"


class Stage:
    """A pipeline stage's directories and files, derived from its name under ingest/<name>/."""

    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    @property
    def root(self) -> Path:
        return BASE_PATH / self.name

    @property
    def inputs(self) -> Path:
        """Fetched sources and curated inputs; only the manifest, the curated inputs and committed query results are tracked."""
        return self.root / "inputs"

    @property
    def outputs(self) -> Path:
        """Tracked artifacts of the build process, such as resolution decisions."""
        return self.root / "outputs"

    @property
    def manifest(self) -> Path:
        return self.inputs / f"{self.name}.manifest.json"

    @property
    def log_file(self) -> Path:
        return self.root / "logs" / f"{self.name}_ingest.log"


MACROREGIONS = Stage("macroregions")
CURRENCIES = Stage("currencies")
SCRIPTS = Stage("scripts")
LANGUAGES = Stage("languages")
COUNTRIES = Stage("countries")
SUBDIVISIONS = Stage("subdivisions")
CITIES = Stage("cities")
# sources several stages read, fetched once by run_pipeline() before any stage
SHARED = Stage("shared")

GEONAMES_DUMP_URL = "https://download.geonames.org/export/dump"
