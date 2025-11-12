from ..database import db, Database
from abc import abstractmethod
from ..dtos import DTO
from typing import TypeVar, Generic
from abc import ABC
import sqlite3
from typing import Type
from .fields import Field, Expression
import json
from villager.utils import sanitize_fts_query
import threading

TDTO = TypeVar("TDTO", bound=DTO)


class Model(Generic[TDTO], ABC):
    db: Database = db
    table_name = ""
    dto_class: Type[TDTO] = None

    id: int
    rank: float

    def __init__(self, id: int, rank: float | None = None, **kwargs):
        self.id = id
        self.rank = rank

    @classmethod
    def from_row(cls, row: sqlite3.Row):
        return cls(**dict(row))

    @abstractmethod
    def to_dto(self) -> TDTO:
        pass

    @classmethod
    def create_table(cls) -> None:
        cls._create_fts()
        cls.db.commit()

    @classmethod
    def count(cls) -> int:
        return cls.db.execute(f"SELECT COUNT(*) FROM {cls.table_name}").fetchone()[0]

    @classmethod
    def columns(cls):
        for name, attr in cls.__dict__.items():
            if isinstance(attr, Field):
                if not attr.index:
                    name = f"{name} UNINDEXED"
                yield name

    @classmethod
    def _create_fts(cls) -> None:
        cls.db.create_fts_table(cls.table_name, cls.columns())

    @classmethod
    def insert_many(cls, data: list[dict]) -> None:
        """Insert multiple rows into the database, requires with atomic."""
        cls.db.insert_many(cls.table_name, data)

    @classmethod
    def get(cls, expr: Expression):
        row = cls.db.execute(
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
            rows = cls.db.execute(
                f"SELECT rowid as id, * FROM {cls.table_name} WHERE {expr.sql} {order_by} {limit}",
                expr.params,
            ).fetchall()
        else:
            rows = cls.db.execute(
                f"SELECT rowid as id, * FROM {cls.table_name} {order_by} {limit}"
            ).fetchall()
        return [cls.from_row(row) for row in rows]

    @classmethod
    def where(cls, sql: str, order_by: str | None = None, limit: int | None = None):
        order_by = f"ORDER BY {order_by}" if order_by else ""
        limit = f"LIMIT {limit}" if limit else ""
        rows = cls.db.execute(
            f"{cls.query_select} {" ".join(cls.query_tables)} WHERE {sql} {order_by} {limit}",
        ).fetchall()
        return [cls.from_row(row) for row in rows]

    @classmethod
    def fts_match(
        cls,
        query: str,
        limit: int | None = 100,
        order_by: list[str] = [],
        exact_match: bool = False,
    ):
        if not query:
            return []

        query = sanitize_fts_query(query)

        if not exact_match:
            tokens = query.split()
            query = " ".join([f"{t}*" for t in tokens])

        q_order_by = "ORDER BY " + ", ".join(order_by) if order_by else ""

        q_limit = "LIMIT ?" if limit is not None else ""

        q = f"""SELECT rowid as id, *, bm25({cls.table_name}, 50.0) as rank FROM {cls.table_name}
                    WHERE {cls.table_name} MATCH ?
                    {q_order_by}
                    {q_limit}"""

        params = (query, limit) if limit is not None else (query,)

        cursor = cls.db.execute(q, params)
        rows: list[sqlite3.Row] = cursor.fetchall()
        cursor.close()
        return [cls.from_row(row) for row in rows if row]

    def __str__(self):
        return json.dumps(self.__dict__, indent=4)
