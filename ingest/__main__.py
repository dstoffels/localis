import argparse
import subprocess
import sys

from ingest.macroregions.scripts import ingest_macroregions
from ingest.currencies.scripts import ingest_currencies
from ingest.scripts.scripts import ingest_scripts
from ingest.languages.scripts import ingest_languages
from ingest.countries.scripts import ingest_countries
from ingest.subdivisions.scripts import ingest_subdivisions
from ingest.cities.scripts import ingest_cities
from ingest.shared.scripts import fetch_shared_sources
from ingest.utils import REPO_PATH, SHARED, ingest_log, reset_staging, mark_complete, promote
from ingest.utils.change_report import write_change_report


def _reconcile_gate() -> None:
    """Runs analysis's data-only step against the staged build; its counts failing to reconcile stops the run before promotion."""
    print("Reconciling the staged build...")
    subprocess.run([sys.executable, "-m", "tests.analysis", "--data-only", "--staging"], cwd=REPO_PATH, check=True)


def run_pipeline() -> None:
    """Builds every stage from its inputs into staging, then promotes the whole build to the repo only once every stage has dumped and the staged counts reconcile."""
    reset_staging()
    with ingest_log.stage(SHARED):
        fetch_shared_sources()
    macroregions = ingest_macroregions()
    currencies = ingest_currencies()
    scripts = ingest_scripts()
    languages = ingest_languages(scripts)
    countries = ingest_countries(macroregions, currencies, scripts, languages)
    subdivisions = ingest_subdivisions(countries)
    ingest_cities(countries, subdivisions)

    mark_complete()
    _reconcile_gate()
    write_change_report()
    promote()
    print("Promoted the build")


def main() -> None:
    argparse.ArgumentParser(description="Runs the data pipeline: every stage builds from its inputs, downloading only what changed, and the build is promoted to src/localis/data only when the whole pipeline succeeds.").parse_args()
    run_pipeline()


if __name__ == "__main__":
    main()
