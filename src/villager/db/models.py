from .database import db
from abc import abstractmethod
from .dtos import Country, Subdivision, SubdivisionBasic, Locality
from typing import TypeVar, Generic
from abc import ABC
import sqlite3
from dataclasses import dataclass
from typing import Type
from .fields import (
    AutoField,
    CharField,
    IntegerField,
    FloatField,
    ForeignKeyField,
    Field,
    Expression,
)
from ..utils import (
    normalize,
    tokenize,
    extract_iso_code,
    parse_other_names,
)

T = TypeVar("T")


@dataclass
class RowData(Generic[T]):
    id: int
    dto: T
    tokens: str
    normalized_name: str

    def __iter__(self):
        yield self.id
        yield self.dto
        yield self.tokens
        yield self.normalized_name


class BaseModel(Generic[T], ABC):
    table_name: str = ""
    dto_class: Type[T] = None
    base_query: str = ""

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> RowData[T]:
        if not row:
            return None

        data = {k: row[k] for k in row.keys() if k in cls.dto_class.__annotations__}
        id = row["id"]
        tokens = row["tokens"]
        normalized_name = row["normalized_name"]
        return RowData(id, cls.dto_class(**data), tokens, normalized_name)

    @classmethod
    def create_table(cls) -> None:
        fields = []
        indexes = []

        for name in dir(cls):
            attr = getattr(cls, name)
            if isinstance(attr, Field):
                fields.append(attr.get_sql())
                if attr.index:
                    indexes.append(attr.get_idx(name, cls.table_name))

        columns = ", ".join(fields)
        db.create_table(cls.table_name, columns)
        for index in indexes:
            db.execute(index)
        cls._create_fts()
        db.commit()

    @classmethod
    def count(cls) -> int:
        return db.execute(f"SELECT COUNT(*) FROM {cls.table_name}").fetchone()[0]

    @classmethod
    def _create_fts(cls) -> None:
        db.create_fts_table(cls.table_name + "_fts", ["tokens"])

    @classmethod
    @abstractmethod
    def parse_raw(cls, raw_data: dict) -> str:
        pass

    @classmethod
    def insert_many(cls, data: list[dict], fts_data: list[dict] = None) -> None:
        db.insert_many(cls.table_name, data)
        if fts_data:
            db.insert_many(cls.table_name + "_fts", fts_data)

    @classmethod
    def get(cls, expr: Expression) -> RowData[T] | None:

        row = db.execute(
            f"{cls.base_query} WHERE {expr.sql} LIMIT 1", expr.params
        ).fetchone()

        if not row:
            return None

        return cls.from_row(row)

    @classmethod
    def select(
        cls,
        expr: Expression | None = None,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[RowData[T]]:
        order_by = f"ORDER BY {order_by}" if order_by else ""
        limit = f"LIMIT {limit}" if limit else ""

        alias = cls.table_name[0]
        if expr:
            rows = db.execute(
                f"{cls.base_query} WHERE {expr.sql} {order_by} {limit}",
                expr.params,
            ).fetchall()
        else:
            rows = db.execute(f"{cls.base_query} {order_by} {limit}").fetchall()
        return [cls.from_row(row) for row in rows]

    @classmethod
    def where(
        cls, sql: str, order_by: str | None = None, limit: int | None = None
    ) -> list[RowData[T]]:
        order_by = f"ORDER BY {order_by}" if order_by else ""
        limit = f"LIMIT {limit}" if limit else ""
        rows = db.execute(
            f"{cls.base_query} WHERE {sql} {order_by} {limit}",
        ).fetchall()
        return [cls.from_row(row) for row in rows]

    @classmethod
    def fts_match(cls, query: str) -> list[RowData[T]]:
        tokens = query.split(" ")
        fts_q = " ".join([f"{t}*" for t in tokens])
        rows = db.execute(cls.base_query + " WHERE tokens MATCH ?", (fts_q,)).fetchall()
        return [cls.from_row(row) for row in rows]


class CountryModel(BaseModel[Country]):
    table_name = "countries"
    dto_class = Country
    base_query = "SELECT c.*, f.tokens as tokens FROM countries_fts f JOIN countries c ON f.rowid = c.id"

    id = AutoField()
    name = CharField(index=True, nullable=False)
    normalized_name = CharField(index=True, nullable=False)
    alpha2 = CharField(unique=True, index=True)
    alpha3 = CharField(unique=True, index=True)
    numeric = IntegerField(unique=True)
    long_name = CharField()

    @classmethod
    def parse_raw(cls, raw_data):
        base = {
            "name": raw_data["name_short"],
            "normalized_name": normalize(raw_data["name_short"]),
            "alpha2": raw_data["#country_code_alpha2"],
            "alpha3": raw_data["country_code_alpha3"],
            "numeric": int(raw_data["numeric_code"]),
            "long_name": raw_data["name_long"],
        }

        fts = {
            "tokens": tokenize(
                raw_data["name_short"],
                raw_data["#country_code_alpha2"],
                raw_data["country_code_alpha3"],
            )
        }
        return base, fts


class SubdivisionModel(BaseModel[Subdivision]):
    table_name = "subdivisions"
    dto_class = Subdivision
    base_query = """SELECT
                    s.id as id,
                    s.name as name,
                    s.normalized_name as normalized_name,
                    s.iso_code as iso_code,
                    s.alt_name as alt_name,
                    s.code as code,
                    s.category as category,
                    s.parent_iso_code as parent_iso_code,
                    s.admin_level as admin_level,

                    c.name as country,
                    c.alpha2 as country_alpha2,
                    c.alpha3 as country_alpha3,
                    f.tokens as tokens
                    FROM subdivisions_fts f
                    JOIN subdivisions s ON f.rowid = s.id
                    JOIN countries c ON s.country_id = c.id
                    """

    id = AutoField()
    name = CharField(index=True, nullable=False)
    normalized_name = CharField(index=True, nullable=False)
    iso_code = CharField(unique=True)
    alt_name = CharField(index=True, nullable=True)
    code = CharField()
    category = CharField(index=True, nullable=True)
    parent_iso_code = CharField(index=True, nullable=True)
    admin_level = IntegerField(default=1)
    country_id: CountryModel = ForeignKeyField(references="countries")

    @classmethod
    def parse_raw(cls, raw_data):
        country_id, country, *_ = CountryModel.get(
            CountryModel.alpha2 == raw_data["#country_code_alpha2"]
        )

        iso_code = raw_data["subdivision_code_iso3166-2"]
        name = raw_data["subdivision_name"]

        base = {
            "name": name,
            "normalized_name": normalize(name),
            "iso_code": iso_code,
            "code": iso_code.split("-")[-1] if "-" in iso_code else iso_code,
            "category": raw_data.get("category", None),
            "country_id": country_id,
            "alt_name": raw_data.get("localVariant", None),
            "parent_iso_code": raw_data.get("parent_subdivision"),
        }

        fts = {
            "tokens": tokenize(
                name,
                country.alpha2,
                country.name,
            )
        }

        return base, fts


class LocalityModel(BaseModel[Locality]):
    table_name = "localities"
    dto_class = Locality
    base_query = """SELECT l.*, 
                    c.name as country, 
                    c.alpha2 as country_alpha2, 
                    c.alpha3 as country_alpha3,
                    s1.name as sub1_name, 
                    s1.iso_code as sub1_iso_code, 
                    s1.code as sub1_code, 
                    s1.category as sub1_category, 
                    s1.admin_level as sub1_admin_level,
                    s2.name as sub2_name, 
                    s2.iso_code as sub2_iso_code, 
                    s2.code as sub2_code, 
                    s2.category as sub2_category, 
                    s2.admin_level as sub2_admin_level,
                    f.tokens as tokens
                FROM localities l
                JOIN subdivisions s1 ON l.subdivision_id = s1.id
                JOIN countries c ON l.country_id = c.id
                LEFT JOIN subdivisions s2 ON s1.parent_iso_code = s2.iso_code
                JOIN localities_fts f ON l.id = f.rowid"""

    id = AutoField()
    name = CharField(index=True, nullable=False)
    normalized_name = CharField(index=True, nullable=False)
    classification = CharField()
    population = IntegerField(nullable=True)
    lat = FloatField()
    lng = FloatField()
    osm_id = IntegerField(index=True)
    osm_type = CharField(index=True)
    subdivision_id = ForeignKeyField(references="subdivisions")
    country_id = ForeignKeyField(references="countries")

    @classmethod
    def parse_raw(cls, raw_data) -> tuple[dict | None, dict | None]:
        # OSM
        osm_id = raw_data.get("osm_id")
        osm_type = raw_data.get("osm_type")

        if not osm_id or not osm_type:
            return None, None

        osm_type = osm_type[0]

        # Name
        name, other_names = parse_other_names(
            raw_data.get("name", None), raw_data.get("other_names", {})
        )
        if not name:
            return None, None

        # Address Data
        address: dict = raw_data.get("address", {})
        if not address:
            return None, None

        country_alpha2 = address.get("country_code")

        lng, lat = raw_data.get("location", (None, None))

        # Subdivision
        sub_iso_code = extract_iso_code(address)
        sub_data = SubdivisionModel.get(SubdivisionModel.iso_code == sub_iso_code)
        if not sub_data:
            return None, None
        subdivision_id, subdivision, *_ = sub_data

        # Country
        country_id, country, *_ = CountryModel.get(
            CountryModel.alpha2 == country_alpha2
        )

        base = {
            "name": name,
            "normalized_name": normalize(name),
            "classification": raw_data["classification"],
            "population": raw_data.get("population", None),
            "lat": lat,
            "lng": lng,
            "osm_id": osm_id,
            "osm_type": osm_type,
            "country_id": country_id,
            "subdivision_id": subdivision_id,
        }

        fts = {
            "tokens": tokenize(
                raw_data["name"],
                subdivision.code,
                subdivision.name,
                country.alpha2,
                country.name,
            )
        }

        return base, fts

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> RowData[T]:
        data = {k: row[k] for k in row.keys() if k in cls.dto_class.__annotations__}
        id = row["id"]
        tokens = row["tokens"]
        normalized_name = row["normalized_name"]

        subdivisions = []
        if row["sub1_name"]:
            subdivisions.append(
                SubdivisionBasic(
                    name=row["sub1_name"],
                    iso_code=row["sub1_iso_code"],
                    code=row["sub1_code"],
                    category=row["sub1_category"],
                    admin_level=row["sub1_admin_level"],
                )
            )

        if row["sub2_name"]:
            subdivisions.append(
                SubdivisionBasic(
                    name=row["sub2_name"],
                    iso_code=row["sub2_iso_code"],
                    code=row["sub2_code"],
                    category=row["sub2_category"],
                    admin_level=row["sub2_admin_level"],
                )
            )
        data["villager_id"] = f'{row["osm_type"]}:{row["osm_id"]}'
        data["subdivisions"] = subdivisions
        data["display_name"] = f'{row["name"]}, {row['sub1_name']}, {row["country"]}'
        return RowData(id, cls.dto_class(**data), tokens, normalized_name)
