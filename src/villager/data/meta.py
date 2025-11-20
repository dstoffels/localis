from villager.data import db, Database


class MetaStore:
    """A simple model and cache for a meta table for storing flags"""

    db: Database = db

    def __init__(self):
        self._cache = {}

    @classmethod
    def create_table(cls):
        cls.db.execute(
            """
                CREATE TABLE IF NOT EXISTS meta(
                    key TEXT PRIMARY KEY,
                    value TEXT)"""
        )

        cls.db.execute("UPDATE meta SET value = 0 WHERE value = 1")
        cls.db.commit()

    def get(self, key: str):

        if key in self._cache:
            return self._cache[key]

        row = self.db.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()

        value = row["value"] if row else None
        self._cache[key] = value
        return value

    def set(self, key: str, value: str):
        self.db.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value)
        )
        self.db.commit()
        self._cache[key] = value
