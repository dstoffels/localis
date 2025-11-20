from villager.data import db, CountryModel, SubdivisionModel, CityModel, MetaStore
from villager.utils import clean_row, chunked
import csv
from pathlib import Path
import zipfile
import argparse

DATA_DIR = Path(__file__).parent


def ingest_countries() -> None:
    countries: list[dict] = []

    with open(DATA_DIR / "countries/countries.tsv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            countries.append(clean_row(row))

    with db.atomic():
        for batch in chunked(list(countries), 100):
            try:
                CountryModel.insert_many(batch)
            except Exception as e:
                print(f"Unexpected error on batch: {e}")
                raise e


def ingest_subdivisions() -> None:
    subdivisions: list[dict] = []

    with open(
        DATA_DIR / "subdivisions/subdivisions.tsv", newline="", encoding="utf-8"
    ) as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            row.pop("id")
            subdivisions.append(clean_row(row))

    with db.atomic():
        for batch in chunked(list(subdivisions), 100):
            try:
                SubdivisionModel.insert_many(batch)
            except Exception as e:
                print(f"Unexpected error on batch: {e}")
                raise e


def ingest_cities() -> None:
    db.create_tables([CityModel])
    with open(DATA_DIR / "cities/cities.tsv", newline="", encoding="utf-8") as f:
        CityModel.load(f)


def compress_db(db_path: str | Path) -> Path:
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")

    with zipfile.ZipFile(
        "src/villager/db/villager_db.zip", "w", compression=zipfile.ZIP_DEFLATED
    ) as zipf:
        zipf.write(db_path, arcname=db_path.name)


def main() -> None:
    parser = argparse.ArgumentParser("options")
    parser.add_argument(
        "--full", "-f", action="store_true", help="Ingest cities into the sqlite db."
    )
    args = parser.parse_args()

    db.drop_tables([CountryModel, SubdivisionModel, CityModel])
    MetaStore.create_table()
    db.create_tables([CountryModel, SubdivisionModel])
    ingest_countries()
    ingest_subdivisions()
    if args.full:
        ingest_cities()

    db.vacuum()


if __name__ == "__main__":
    main()
