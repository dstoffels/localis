from ..database import db
from abc import abstractmethod
from ..dtos import Country, Subdivision, SubdivisionBasic, Locality
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
from ...utils import (
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


class Model(Generic[T], ABC):
    table_name: str = ""
    dto_class: Type[T] = None
    fts_fields: list[str] = []
    query_select: str = ""
    query_tables: str = ""

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

        for name, attr in cls.__dict__.items():
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
        db.create_fts_table(cls.table_name + "_fts", cls.fts_fields)

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
            f"{cls.query_select} {" ".join(cls.query_tables)} WHERE {expr.sql} LIMIT 1",
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
    ) -> list[RowData[T]]:
        order_by = f"ORDER BY {order_by}" if order_by else ""
        limit = f"LIMIT {limit}" if limit else ""

        if expr:
            rows = db.execute(
                f"{cls.query_select} {" ".join(cls.query_tables)} WHERE {expr.sql} {order_by} {limit}",
                expr.params,
            ).fetchall()
        else:
            rows = db.execute(
                f"{cls.query_select} {" ".join(cls.query_tables)} {order_by} {limit}"
            ).fetchall()
        return [cls.from_row(row) for row in rows]

    @classmethod
    def where(
        cls, sql: str, order_by: str | None = None, limit: int | None = None
    ) -> list[RowData[T]]:
        order_by = f"ORDER BY {order_by}" if order_by else ""
        limit = f"LIMIT {limit}" if limit else ""
        rows = db.execute(
            f"{cls.query_select} {" ".join(cls.query_tables)} WHERE {sql} {order_by} {limit}",
        ).fetchall()
        return [cls.from_row(row) for row in rows]

    @classmethod
    def fts_match(
        cls, query: str, limit=100, exact: bool = False, addl_clause: str = ""
    ) -> list[RowData[T]]:
        if not exact:
            tokens = query.split()
            query = " ".join([f"{t}*" for t in tokens])

        fts_table = cls.table_name + "_fts"
        tables = [t for t in cls.query_tables]
        table_prefix = cls.table_name[0]
        tables[0] = f"FROM matched\n"

        matched = f"""WITH matched AS (
            SELECT rowid, * FROM {fts_table}
            WHERE {fts_table} MATCH ?
            {addl_clause}
            ORDER BY bm25({fts_table}, 3.0, 1.5, 1.0, 1.0)
            LIMIT ?
        )
        """

        fts_q = f"""{matched} {cls.query_select} {" ".join(tables)} 
                    LIMIT ?"""

        rows = db.execute(
            fts_q,
            (query, limit, limit),
        ).fetchall()
        return [cls.from_row(row) for row in rows]
