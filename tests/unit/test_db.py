from localis.data import (
    Database,
    MetaStore,
    CountryModel,
    SubdivisionModel,
    CityModel,
    Model,
    db as DB,
)
import pytest
import sqlite3


@pytest.fixture(scope="module")
def db():
    """A memory-bound sqlite db for testing."""

    orig_path = DB.get_db_path()
    DB.set_db_path(":memory:")

    yield DB

    DB.set_db_path(orig_path)


@pytest.fixture(scope="function")
def create_test_table(db: Database):
    def callback():
        db.create_table("test", "id INTEGER PRIMARY KEY")

    yield callback

    db.drop_tables(["test"])


class TestTables:
    """TABLES"""

    @pytest.mark.parametrize("model_cls", [CountryModel, SubdivisionModel, CityModel])
    def test_create_table(self, db: Database, model_cls: Model):
        """should"""
        db.create_tables([model_cls])
        db.commit()

        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            params=(model_cls.table_name,),
        )

        result = cursor.fetchone()[0]

        assert result == model_cls.table_name


class TestConnection:
    """DB CONNECTION"""

    def init_conn(self, db: Database):
        """should employ a connection called :memory:"""
        assert db._conn is not None
        assert isinstance(db._conn, sqlite3.Connection)
        assert db.db_path == ":memory:"

    def test_reconnect(self, db: Database):
        """should close and re-establish connection"""
        db.close()
        assert db._conn is None

        db.connect()
        assert db._conn is not None

    def test_atomic(self, db: Database, create_test_table):
        """should manage conn using 'with' syntax"""
        create_test_table()
        COUNT = 3

        with db.atomic():
            db.execute_many(
                f"INSERT INTO test (id) VALUES (?)", [(n,) for n in range(COUNT)]
            )

        cursor = db.execute("SELECT COUNT(*) FROM test")
        assert cursor.fetchone()[0] == COUNT

    def test_atomic_rollback(self, db: Database, create_test_table):
        """should rollback db changes on exception"""
        create_test_table()

        with pytest.raises(ValueError):
            with db.atomic():
                db.execute("INSERT INTO test (id) VALUES (1)")
                raise ValueError("OPE")

        cursor = db.execute("SELECT COUNT(*) FROM test")
        assert cursor.fetchone()[0] == 0


class TestMetaStore:
    """META"""

    kvp_param = pytest.mark.parametrize("kvp", [{"test_key": "test_value"}])

    @pytest.fixture(scope="class")
    def metastore(self):
        return MetaStore()

    def test_create(self, db: Database):
        """should create the meta table"""

        table_name = "meta"
        MetaStore.create_table()

        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            params=(table_name,),
        )

        result = cursor.fetchone()[0]

        assert result == table_name

    @kvp_param
    def test_set(self, metastore: MetaStore, kvp: dict, db: Database):
        """should set a new kvp in the metastore"""

        for key, value in kvp.items():
            metastore.set(key, value)
            cursor = db.execute("SELECT value FROM meta WHERE key = ?", (key,))
            result = cursor.fetchone()[0]
            assert result == value

    @kvp_param
    def test_get(self, metastore: MetaStore, kvp: dict):
        """should retrieve value from the meta table by key"""

        for key, value in kvp.items():
            result = metastore.get(key)
            assert result == value
