from villager.db import db, CountryModel, SubdivisionModel, LocalityModel
import csv
from pathlib import Path
import hashlib
import zipfile
import json


def run() -> None:
    db.create_tables([CountryModel, SubdivisionModel, LocalityModel])
    ingest_countries()
    ingest_subdivisions()
    ingest_localities()
    db.vacuum()
    compress_db(db.db_path)


DATA_DIR = Path(__file__).parent.parent / "data"


def chunked(list: list, size: int):
    for i in range(0, len(list), size):
        yield list[i : i + size]


def ingest_countries() -> None:
    parsed: list[tuple[dict, dict]] = []

    with open(DATA_DIR / "countries.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for line in reader:
            parsed.append(CountryModel.parse_raw(line))

    with db.atomic():
        for batch in chunked(parsed, 100):
            try:
                data, fts = zip(*batch)
                CountryModel.insert_many(data, fts)
            except Exception as e:
                print(f"Unexpected error on batch: {e}")
                raise e


def ingest_subdivisions() -> None:
    subdivisions: list[tuple[dict, dict]] = []
    seen = set()

    with open(DATA_DIR / "subdivisions.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for line in reader:
            data, fts = SubdivisionModel.parse_raw(line)
            if data.get("iso_code") in seen:
                continue
            seen.add(data.get("iso_code"))
            subdivisions.append((data, fts))

    with db.atomic():
        for batch in chunked(subdivisions, 100):
            try:
                data, fts = zip(*batch)
                SubdivisionModel.insert_many(data, fts)
            except Exception as e:
                print(f"Unexpected error on batch: {e}")
                raise e


def ingest_localities() -> None:
    locality_dir = DATA_DIR / "localities"

    localities: list[tuple[dict, dict]] = []
    seen = set()

    for c_dir in locality_dir.iterdir():
        if not c_dir.is_dir():
            continue

        for file in c_dir.iterdir():
            if not file.is_file():
                continue

            if "hamlet" in file.stem.lower():
                continue

            classification = file.stem.replace("place-", "")

            with file.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data: dict = json.loads(line)

                        data["classification"] = classification

                        data, fts = LocalityModel.parse_raw(data)

                        if data and fts:
                            hash = hashlib.sha256(
                                f"{data.get('name')}{data.get('subdivision_id')}".encode()
                            ).hexdigest()
                            if hash in seen:
                                continue
                            seen.add(hash)

                            localities.append((data, fts))

                    except json.JSONDecodeError as e:
                        print(f"Error Decoding JSON: {e}")
                        continue
                    except Exception as e:
                        print(f"Unexpected error on line: {line}")
                        raise e
    with db.atomic():
        for batch in chunked(localities, 1000):
            try:
                data, fts = zip(*batch)
                LocalityModel.insert_many(data, fts)
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


if __name__ == "__main__":
    run()
