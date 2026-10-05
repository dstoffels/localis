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
from ingest.utils import REPO_PATH, SHARED, ingest_log, pipeline_log, reset_staging, mark_complete, promote
from ingest.utils.change_report import write_change_report


def _analysis(*args: str) -> None:
    """Runs the analysis suite with args, its output going to the pipeline log; a failure exits with analysis's own error."""
    result = subprocess.run([sys.executable, "-m", "tests.analysis", *args], cwd=REPO_PATH, capture_output=True, text=True)
    for line in result.stdout.splitlines():
        pipeline_log.writeline(line)
    if result.returncode:
        print(result.stderr, file=sys.stderr, end="")
        error = result.stderr.strip().splitlines()
        sys.exit(f"analysis {' '.join(args)} failed: {error[-1] if error else f'exit code {result.returncode}'}")


def run_pipeline() -> None:
    """Builds every stage from its inputs into staging, promotes the whole build to the repo only once every stage has dumped and the staged counts reconcile, then regenerates the data stats and docs from it."""
    with pipeline_log.run():
        reset_staging()
        pipeline_log.step("fetching the shared sources")
        with ingest_log.stage(SHARED):
            fetch_shared_sources()
        pipeline_log.step("building macroregions")
        macroregions = ingest_macroregions()
        pipeline_log.step("building currencies")
        currencies = ingest_currencies()
        pipeline_log.step("building scripts")
        scripts = ingest_scripts()
        pipeline_log.step("building languages")
        languages = ingest_languages(scripts)
        pipeline_log.step("building countries")
        countries = ingest_countries(macroregions, currencies, scripts, languages)
        pipeline_log.step("building subdivisions")
        subdivisions = ingest_subdivisions(countries)
        pipeline_log.step("building cities")
        ingest_cities(countries, subdivisions)
        mark_complete()

        pipeline_log.step("checking the staged build")
        _analysis("--staging")
        pipeline_log.step("writing the change reports")
        write_change_report()
        pipeline_log.step("promoting the build")
        promote()
        pipeline_log.promoted = True
        # the data stats and the docs' stat markers, written only once the build they describe has shipped
        pipeline_log.step("regenerating the data stats and docs")
        _analysis("--data-only")


def main() -> None:
    argparse.ArgumentParser(description="Runs the data pipeline: every stage builds from its inputs, downloading only what changed, and the build is promoted to src/localis/data only when the whole pipeline succeeds.").parse_args()
    run_pipeline()


if __name__ == "__main__":
    main()
