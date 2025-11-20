from abc import ABC
from typing import Literal
from typing import Generic, TypeVar

T = TypeVar("T")


class Expression:
    def __init__(self, sql: str, params: tuple = ()):
        self.sql = sql
        self.params = params

    def __and__(self, other):
        return Expression(f"({self.sql} AND {other.sql})", self.params + other.params)

    def __or__(self, other):
        return Expression(f"({self.sql} OR {other.sql})", self.params + other.params)

    def __str__(self):
        return self.sql


class Field(Generic[T], ABC):
    type: Literal["TEXT", "INTEGER", "FLOAT", "BOOLEAN"] = "INTEGER"

    def __init__(
        self,
        *,
        nullable: bool = True,
        default: T | None = None,
        unique: bool = False,
        index: bool = True,
        primary_key: bool = False,
    ):
        self.nullable = nullable
        self.default = default
        self.unique = unique
        self.index = index
        self.primary_key = primary_key
        self.name = None  # set by the model

    def __set_name__(self, owner, name):
        self.name = name
        self.model = owner

    def __get__(self, instance, owner) -> T:
        if instance is None:
            return self
        return instance.__dict__.get(self.name, self.default)

    def __set__(self, instance, value: T):
        instance.__dict__[self.name] = value

    def __eq__(self, other):
        return Expression(f"{self.name} = ?", (str(other),))

    def __ne__(self, other):
        return Expression(f"{self.name} != ?", (str(other),))

    def __lt__(self, other):
        return Expression(f"{self.name} < ?", (str(other),))

    def __le__(self, other):
        return Expression(f"{self.name} <= ?", (str(other),))

    def __gt__(self, other):
        return Expression(f"{self.name} > ?", (str(other),))

    def __ge__(self, other):
        return Expression(f"{self.name} >= ?", (str(other),))

    def like(self, pattern):
        return Expression(f"{self.name} LIKE ?", (pattern,))

    def isin(self, values: list):
        placeholders = ", ".join("?" for _ in values)
        return Expression(f"{self.name} IN ({placeholders})", tuple(values))

    def get_sql(self) -> str:
        parts = [self.name, self.type]
        if self.primary_key:
            parts.append("PRIMARY KEY")
        if not self.nullable:
            parts.append("NOT NULL")
        if self.unique:
            parts.append("UNIQUE")
        if self.default is not None:
            val = self.default
            if isinstance(self.default, str):
                val = f"'{val}'"
            elif isinstance(self.default, bool):
                val = int(val)
            parts.append(f"DEFAULT {self.default}")
        parts.append("COLLATE NOCASE")
        return " ".join(parts)

    def get_idx(self, name: str, table: str) -> str:
        if self.index:
            return f"CREATE INDEX IF NOT EXISTS {table}_{name}_idx ON {table}({name})"
        return ""


class AutoField(Field[int]):
    def get_sql(self):
        return f"{self.name} INTEGER PRIMARY KEY AUTOINCREMENT"


class CharField(Field[str]):
    type = "TEXT"


class IntField(Field[int]):
    pass


class FloatField(Field[float]):
    type = "FLOAT"


class BooleanField(Field[bool]):
    type = "BOOLEAN"


class ForeignKeyField(Field[int]):
    def __init__(
        self,
        *args,
        references: str = "",
        field: str = "id",
        on_delete: Literal[
            "CASCADE", "RESTRICT", "SET NULL", "SET DEFAULT"
        ] = "SET NULL",
        nullable: bool = None,
        **kwargs,
    ):
        if nullable is not None:
            kwargs["nullable"] = nullable
        else:
            kwargs["nullable"] = False
        super().__init__(*args, **kwargs)
        self.references = references
        self.field = field
        self.on_delete = on_delete

    def get_sql(self):
        parts = [
            self.name,
            self.type,
            f"REFERENCES {self.references}({self.field}) ON DELETE {self.on_delete}",
        ]
        if not self.nullable:
            parts.insert(2, "NOT NULL")
        return " ".join(parts)
