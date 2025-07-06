from peewee import SqliteDatabase
import atexit

db = SqliteDatabase("src/villager/db/villager.db")

db.connect()


def ngrams(s: str, n: int) -> set[str]:
    s = f"{' ' * (n - 1)}{s.lower()}{' ' * (n - 1)}"
    return {s[i : i + n] for i in range(len(s) - n + 1)}


def ngram_sim(s1: str, s2: str, n: int) -> float:
    n1, n2 = ngrams(s1, n), ngrams(s2, n)
    if not n1 or not n2:
        return 0.0
    return 2 * len(n1 & n2) / (len(n1) + len(n2))


db.connection().create_function("ngram_sim", 3, ngram_sim)


@atexit.register
def close_db() -> None:
    if not db.is_closed():
        db.close()
