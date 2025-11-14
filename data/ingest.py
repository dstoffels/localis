from villager.db import db, CountryModel, SubdivisionModel, CityModel
import csv
from pathlib import Path
import zipfile
import argparse

DATA_DIR = Path(__file__).parent


def chunked(list: list, size: int):
    for i in range(0, len(list), size):
        yield list[i : i + size]


def clean_row(row: dict[str, str]) -> dict[str, str | None]:
    return {k: (v if v.strip() != "" else None) for k, v in row.items()}


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
    cities: list[dict] = []
    with open(DATA_DIR / "cities/cities.tsv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            MAX_DIGITS = 9
            row["population"] = f"{int(row['population']):0{MAX_DIGITS}d}"
            cities.append(clean_row(row))

    with db.atomic():
        for batch in chunked(list(cities), 1000):
            try:
                CityModel.insert_many(batch)
            except Exception as e:
                print(f"Unexpected error on batch: {e}")
                raise e


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

    db.nuke()
    db.create_tables([CountryModel, SubdivisionModel, CityModel])
    ingest_countries()
    ingest_subdivisions()
    if args.full:
        ingest_cities()
    db.vacuum()
    # compress_db(db.db_path)


if __name__ == "__main__":
    main()
