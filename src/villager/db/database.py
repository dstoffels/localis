import atexit
from typing import Any, Dict, List, Tuple
from contextlib import contextmanager


import sqlite3


class Database:
    MAX_PREFIX = 24

    def __init__(self, db_path: str):
        self.db_path: str = db_path
        self._conn: sqlite3.Connection | None = None
        self._setup_conn()

    def _setup_conn(self) -> None:
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row

        self._conn.execute("PRAGMA journal_mode = OFF")
        self._conn.execute("PRAGMA synchronous = OFF")
        self._conn.execute("PRAGMA temp_store = MEMORY")
        self._conn.execute("PRAGMA cache_size = -100000")
        self._conn.execute("PRAGMA locking_mode = EXCLUSIVE")
        self._conn.execute("PRAGMA mmap_size = 268435456")

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def connect(self) -> None:
        if not self._conn:
            self._setup_conn()

    def commit(self) -> None:
        self._conn.commit()

    def clone(self) -> "Database":
        return Database(self.db_path)

    @contextmanager
    def atomic(self):
        try:
            yield
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def execute(self, query: str, params: Tuple | Dict = ()) -> sqlite3.Cursor:
        """Execute a single query"""
        cursor = self._conn.cursor()
        cursor.execute(query, params)
        return cursor

    def execute_many(
        self, query: str, params_list: List[Tuple | Dict]
    ) -> sqlite3.Cursor:
        """Execute query with multiple parameter sets"""
        cursor = self._conn.cursor()
        cursor.executemany(query, params_list)
        return cursor

    def insert_many(self, table: str, data_list: List[Dict[str, Any]]) -> None:
        """Insert multiple rows"""
        if not data_list:
            return

        column_list = list(data_list[0].keys())
        columns = ", ".join(column_list)
        placeholders = ", ".join(["?" for _ in column_list])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        params_list = [tuple(row[col] for col in column_list) for row in data_list]
        self.execute_many(query, params_list)

    def create_table(self, table_name: str, columns: str) -> None:
        """Create table with given columns definition"""
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})"
        self.execute(query)
        self._conn.commit()

    def create_tables(self, tables: list[object]) -> None:
        for table in tables:
            if hasattr(table, "create_table") and callable(table.create_table):
                table.create_table()

    def drop_tables(self, tables: list[object]) -> None:
        for table in tables:
            if hasattr(table, "drop") and callable(table.drop):
                table.drop()

    def create_fts_table(
        self,
        table_name: str,
        columns: List[str],
    ) -> None:
        """Create FTS5 virtual table"""
        columns_str = ", ".join(columns)

        fts_options = [
            '''tokenize = "unicode61 remove_diacritics 2"''',
            f'prefix="{' '.join([str(i) for i in range(2, self.MAX_PREFIX + 1)])}"',
        ]

        options_str = ", " + ", ".join(fts_options) if fts_options else ""

        query = f"""CREATE VIRTUAL TABLE IF NOT EXISTS "{table_name}" USING fts5({columns_str}{options_str})"""
        self.execute(query)
        self._conn.commit()

    def vacuum(self) -> None:
        """Vacuum database"""
        self.execute("VACUUM")

    def analyze(self) -> sqlite3.Cursor:
        """Analyze database for query optimization"""
        return self.execute("ANALYZE")


db = Database("src/villager/db/villager.db")


@atexit.register
def close_db() -> None:
    db.close()
