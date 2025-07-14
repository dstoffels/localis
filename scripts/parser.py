import csv
from pathlib import Path
import json
from villager.db import (
    db,
    CountryModel,
    SubdivisionModel,
    LocalityModel,
)
import re
from typing import Optional
import hashlib
import zipfile
from villager.utils import normalize

DATA_DIR = Path(__file__).parent.parent / "data"


def run() -> None:
    """
    Connects to the database, runs the data loading functions sequentially,
    then closes the database connection.
    """

    db.execute_sql("PRAGMA journal_mode = OFF;")
    db.execute_sql("PRAGMA synchronous = OFF;")
    db.execute_sql("PRAGMA temp_store = MEMORY;")
    db.execute_sql("PRAGMA cache_size = -100000;")
    db.execute_sql("PRAGMA locking_mode = EXCLUSIVE;")

    load_countries()
    load_subdivisions()
    load_localities()

    db.execute_sql("VACUUM;")
    compress_db(db.database)


def chunked(iterable, size):
    for i in range(0, len(iterable), size):
        yield iterable[i : i + size]


def load_countries() -> None:
    db.create_tables([CountryModel, CountryFTS], safe=True)
    countries = []
    fts_rows: list[dict[str, str]] = []

    with open(DATA_DIR / "countries.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            countries.append(
                {
                    "name": row["name_short"],
                    "normalized_name": normalize(row["name_short"]),
                    "alpha2": row["#country_code_alpha2"],
                    "alpha3": row["country_code_alpha3"],
                    "numeric": int(row["numeric_code"]),
                    "long_name": row["name_long"],
                }
            )

            fts_rows.append(
                {
                    "tokens": tokenize(
                        row["name_short"],
                        row["#country_code_alpha2"],
                        row["country_code_alpha3"],
                    )
                }
            )

    with db.atomic():
        for batch in chunked(countries, 100):
            try:
                CountryModel.insert_many(batch).execute()
            except Exception as e:
                print(f"Unexpected error on batch: {e}")
                raise e
        for batch in chunked(fts_rows, 100):
            try:
                CountryFTS.insert_many(batch).execute()
            except Exception as e:
                print(f"Unexpected error on batch: {e}")
                raise e


def load_subdivisions() -> None:
    db.create_tables([SubdivisionModel, SubdivisionFTS], safe=True)
    subdivisions: list[dict[str, str | None]] = []
    fts_rows: list[dict[str, str]] = []

    with open(DATA_DIR / "subdivisions.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        iso_codes = set()

        for row in reader:
            iso_code = row.get("subdivision_code_iso3166-2", "")
            if iso_code in iso_codes:
                continue
            iso_codes.add(iso_code)

            country_alpha2 = row.get("#country_code_alpha2", "")
            country: CountryModel | None = CountryModel.get_or_none(
                CountryModel.alpha2 == country_alpha2
            )

            subdivisions.append(
                {
                    "name": row["subdivision_name"],
                    "normalized_name": normalize(row["subdivision_name"]),
                    "iso_code": iso_code,
                    "code": iso_code.split("-")[-1] if "-" in iso_code else iso_code,
                    "category": row.get("category") or None,
                    "country": country,
                    "alt_name": row.get("localVariant") or None,
                    "parent_iso_code": row.get("parent_subdivision"),
                }
            )

            fts_rows.append(
                {
                    "tokens": tokenize(
                        row["subdivision_name"],
                        country.alpha2,
                        country.name,
                    )
                }
            )

    # insert all subs w/o parent
    with db.atomic():
        for batch in chunked(subdivisions, 100):
            try:
                SubdivisionModel.insert_many(batch).execute()
            except Exception as e:
                print(f"Unexpected error on batch: {e}")
                raise e

        for batch in chunked(fts_rows, 100):
            try:
                SubdivisionFTS.insert_many(batch).execute()
            except Exception as e:
                print(f"Unexpected error on batch: {e}")
                raise e

    # Assign parents & admin level
    data_by_iso = {item["iso_code"]: item for item in subdivisions}
    subs_by_iso = {sub.iso_code: sub for sub in SubdivisionModel.query_select()}

    with db.atomic():
        for sub in subs_by_iso.values():
            sub: SubdivisionModel
            original_data = data_by_iso.get(sub.iso_code)
            parent_iso_code = original_data.get("parent_iso_code")
            parent: SubdivisionModel = subs_by_iso.get(parent_iso_code)
            if parent:
                sub.parent = parent
                sub.admin_level = parent.admin_level + 1
        SubdivisionModel.bulk_update(
            subs_by_iso.values(), fields=["parent", "admin_level"]
        )


def load_localities() -> None:
    db.create_tables([LocalityModel], safe=True)
    LocalityFTS.create_table()
    locality_dir = DATA_DIR / "localities"
    localities = []
    fts_rows = []
    country_map = {c.alpha2: c for c in CountryModel.query_select()}
    sub_map = {s.iso_code: s for s in SubdivisionModel.query_select()}

    seen = set()

    for country_dir in locality_dir.iterdir():
        if not country_dir.is_dir():
            continue

        for file in country_dir.iterdir():
            if not file.is_file():
                continue

            # Skip hamlet files
            if "hamlet" in file.stem.lower():
                continue

            classification = file.stem.replace("place-", "")

            with file.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data: dict = json.loads(line)

                        # build id

                        osm_id: int = data.get("osm_id")
                        if not osm_id:
                            continue

                        osm_type: str = data.get("osm_type")
                        if not osm_type:
                            continue

                        osm_type = osm_type[0]

                        comp_id = f"{osm_type}:{osm_id}"

                        if comp_id in seen:
                            continue
                        seen.add(comp_id)

                        # build name

                        name, other_names = parse_other_names(
                            data.get("name", None), data.get("other_names", {})
                        )
                        if not name:
                            continue

                        address: dict = data.get("address", {})
                        if not address:
                            continue

                        lng, lat = data.get("location", (None, None))

                        sub_iso_code = extract_iso_code(address)
                        subdivision: SubdivisionModel = sub_map.get(sub_iso_code)
                        if not subdivision:
                            continue

                        country: CountryModel = country_map.get(
                            address.get("country_code", "").upper()
                        )

                        hashed_name_admin1 = hashlib.sha256(
                            f"{name}{subdivision.iso_code}".encode()
                        ).hexdigest()

                        if hashed_name_admin1 in seen:
                            continue
                        seen.add(hashed_name_admin1)

                        localities.append(
                            {
                                "osm_id": osm_id,
                                "osm_type": osm_type,
                                "name": name,
                                "normalized_name": normalize(name),
                                "subdivision": subdivision,
                                "country": country,
                                "lat": lat,
                                "lng": lng,
                                "classification": classification,
                                "population": data.get("population", None),
                            }
                        )

                        fts_rows.append(
                            {
                                "tokens": tokenize(
                                    name,
                                    subdivision.code,
                                    subdivision.name,
                                    country.alpha2,
                                    country.name,
                                )
                            }
                        )

                    except json.JSONDecodeError as e:
                        print(f"Error decoding JSON: {e}")
                        continue
                    except Exception as e:
                        print(f"Unexpected error on line: {line}")
                        raise e

    with db.atomic():
        for batch in chunked(localities, 100):
            try:
                LocalityModel.insert_many(batch).execute()
            except Exception as e:
                print(f"Unexpected error on batch: {e}")
                raise e
        for batch in chunked(fts_rows, 100):
            try:
                LocalityFTS.insert_many(batch).execute()
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
