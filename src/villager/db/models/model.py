from ..database import db
from abc import abstractmethod
from ..dtos import Country, Subdivision, SubdivisionBasic, City, DTO
from typing import TypeVar, Generic
from abc import ABC
import sqlite3
from dataclasses import dataclass
from typing import Type
from .fields import (
    Field,
    Expression,
    AutoField,
    BooleanField,
    CharField,
    FloatField,
    ForeignKeyField,
    IntegerField,
)
from ...utils import (
    normalize,
    tokenize,
    extract_iso_code,
    parse_other_names,
)

TDTO = TypeVar("TDTO", bound=DTO)


@dataclass
class RowData(Generic[TDTO]):
    id: int
    dto: TDTO
    search_tokens: str

    def __iter__(self):
        yield self.id
        yield self.dto
        yield self.search_tokens


class Model(Generic[TDTO], ABC):
    table_name: str = ""
    dto_class: Type[TDTO] = None
    search_tokens: str = ""

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> RowData[TDTO]:
        if not row:
            return None

        data = {k: row[k] for k in row.keys() if k in cls.dto_class.__annotations__}
        dto = cls.dto_class(**data)
        return RowData(row["id"], dto, cls.search_tokens.lower())

    @classmethod
    def create_table(cls) -> None:
        cls._create_fts()
        db.commit()

    @classmethod
    def count(cls) -> int:
        return db.execute(f"SELECT COUNT(*) FROM {cls.table_name}").fetchone()[0]

    @classmethod
    def columns(cls):
        for name, attr in cls.__dict__.items():
            if isinstance(attr, Field):
                if not attr.index:
                    name = f"{name} UNINDEXED"
                yield name

    @classmethod
    def _create_fts(cls) -> None:
        db.create_fts_table(cls.table_name, cls.columns())

    # @classmethod
    # @abstractmethod
    # def parse_raw(cls, raw_data: dict) -> str:
    #     pass

    @classmethod
    def insert_many(cls, data: list[dict]) -> None:
        """Insert multiple rows into the database, requires with atomic."""
        db.insert_many(cls.table_name, data)

    @classmethod
    def get(cls, expr: Expression) -> TDTO | None:
        row = db.execute(
            f"SELECT rowid as id, * FROM {cls.table_name} WHERE {expr.sql} LIMIT 1",
            expr.params,
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
    ) -> list[TDTO]:

        order_by = f"ORDER BY {order_by}" if order_by else ""
        limit = f"LIMIT {limit}" if limit else ""

        if expr:
            rows = db.execute(
                f"SELECT * FROM {cls.table_name} WHERE {expr.sql} {order_by} {limit}",
                expr.params,
            ).fetchall()
        else:
            rows = db.execute(
                f"SELECT * FROM {cls.table_name} {order_by} {limit}"
            ).fetchall()
        return [cls.from_row(row) for row in rows]

    @classmethod
    def where(
        cls, sql: str, order_by: str | None = None, limit: int | None = None
    ) -> list[RowData[TDTO]]:
        order_by = f"ORDER BY {order_by}" if order_by else ""
        limit = f"LIMIT {limit}" if limit else ""
        rows = db.execute(
            f"{cls.query_select} {" ".join(cls.query_tables)} WHERE {sql} {order_by} {limit}",
        ).fetchall()
        return [cls.from_row(row) for row in rows]

    @classmethod
    def fts_match(
        cls, query: str, limit=100, order_by="", exact: bool = False
    ) -> list[RowData[TDTO]]:
        if not exact:
            tokens = query.split()
            query = " ".join([f"{t}*" for t in tokens])
        order_by = f", {order_by}" if order_by else ""

        fts_q = f"""SELECT rowid as id, *, bm25({cls.table_name}, 50.0) as rank FROM {cls.table_name}
                    WHERE {cls.table_name} MATCH ?
                    ORDER BY rank{order_by}
                    LIMIT ?"""

        rows = db.execute(fts_q, (query, limit)).fetchall()
        return [cls.from_row(row) for row in rows]

    @classmethod
    def truncate(cls):
        db.truncate(cls.table_name)
