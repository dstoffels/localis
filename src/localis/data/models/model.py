from localis.data import db, Database
from localis.data.models.fields import Field, Expression
from localis.dtos import DTO
from typing import TypeVar, Generic
from abc import ABC
import sqlite3
from typing import Type
import json
from abc import abstractmethod
from localis.utils import prep_fts_tokens

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
        data = self.__dict__
        data.pop("rank")
        return self.dto_class(**data)

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
    def drop(cls):
        cls.db.execute(f"DROP TABLE IF EXISTS {cls.table_name}")
        cls.db.commit()
        cls.db.vacuum()

    @classmethod
    def insert_many(cls, data: list[dict]) -> None:
        """Insert multiple rows into the database, requires with atomic."""
        cls.db.insert_many(cls.table_name, data)

    def __str__(self):
        return json.dumps(self.__dict__, indent=4)

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
    def get_by_id(cls, id: int):
        row = cls.db.execute(
            f"SELECT rowid as id, * FROM {cls.table_name} WHERE id = ? LIMIT 1", (id,)
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
    ) -> list["Model"]:

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
    def fts_match(
        cls,
        query: str = None,
        field_queries: dict[str, str] = None,
        exact_match: bool = True,
        order_by: list[str] = [],
        limit: int = None,
        offset: int = None,
    ):
        if field_queries:
            params = list(
                prep_fts_tokens(q, exact_match) for q in field_queries.values()
            )
            q_where = "WHERE " + "AND ".join(
                f"{col} MATCH ?" for col in field_queries.keys()
            )
        elif query:
            sanitized_input = prep_fts_tokens(query, exact_match)

            params = [sanitized_input]
            q_where = f"WHERE {cls.table_name} MATCH ?"
        else:
            return []

        bm25 = f", bm25({cls.table_name}, 50.0) as rank" if "rank" in order_by else ""

        q_order_by = "ORDER BY " + ", ".join(order_by) if order_by else ""

        q_limit = "LIMIT ?" if limit is not None else ""

        q_offset = f"OFFSET ?" if offset is not None else ""

        q = f"""SELECT rowid as id, *{bm25} FROM {cls.table_name}
                    {q_where}
                    {q_order_by}
                    {q_limit}
                    {q_offset}"""

        if limit:
            params.append(limit)

        if offset:
            params.append(offset)

        cursor = cls.db.execute(q, params)
        rows: list[sqlite3.Row] = cursor.fetchall()
        cursor.close()
        return [cls.from_row(row) for row in rows if row]
