from peewee import SqliteDatabase
import atexit

db = SqliteDatabase("src/villager/db/villager.db")

db.connect()


def trigram_similarity(s1: str, s2: str) -> float:
    s1, s2 = s1.lower(), s2.lower()

    def trigrams(s):
        s = f"  {s}  "
        return {s[i : i + 3] for i in range(len(s) - 2)}

    t1, t2 = trigrams(s1), trigrams(s2)
    if not t1 or not t2:
        return 0.0
    return 200 * len(t1 & t2) / (len(t1) + len(t2))


db.connection().create_function("trigram_sim", 2, trigram_similarity)


@atexit.register
def close_db() -> None:
    if not db.is_closed():
        db.close()
