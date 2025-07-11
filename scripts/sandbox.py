# # from rapidfuzz import fuzz
# # from typing import List, Tuple
# # from peewee import fn
# # from models import Locality, LocalityFTS

# # MIN_TOKEN_LEN = 2
# # MAX_CANDIDATES = 500
# # FUZZY_THRESHOLD = 85

# # # Field scoring weights
# # FIELD_WEIGHTS = {
# #     "name": 0.5,
# #     "subdivision_name": 0.2,
# #     "subdivision_code": 0.1,
# #     "country_name": 0.15,
# #     "country_code": 0.05,
# # }


# # def tokenize(query: str) -> List[str]:
# #     return query.lower().split()


# # def fts_query(tokens: List[str]) -> str:
# #     return " ".join(f"{t}*" for t in tokens if len(t) >= MIN_TOKEN_LEN)


# # def get_candidates(query_tokens: List[str]) -> List[Locality]:
# #     match_query = fts_query(query_tokens)
# #     return (
# #         Locality.select()
# #         .join(LocalityFTS, on=(Locality.id == LocalityFTS.rowid))
# #         .where(LocalityFTS.full_text.match(match_query))
# #         .limit(MAX_CANDIDATES)
# #     )


# # def fuzzy_score(query: str, loc: Locality) -> float:
# #     return (
# #         FIELD_WEIGHTS["name"] * fuzz.token_set_ratio(query, loc.name or "")
# #         + FIELD_WEIGHTS["subdivision_name"]
# #         * fuzz.token_set_ratio(query, loc.subdivision_name or "")
# #         + FIELD_WEIGHTS["subdivision_code"]
# #         * fuzz.token_set_ratio(query, loc.subdivision_code or "")
# #         + FIELD_WEIGHTS["country_name"]
# #         * fuzz.token_set_ratio(query, loc.country_name or "")
# #         + FIELD_WEIGHTS["country_code"]
# #         * fuzz.token_set_ratio(query, loc.country_code or "")
# #     )


# # def search_localities(query: str) -> List[Tuple[Locality, float]]:
# #     base_tokens = tokenize(query)
# #     token_lengths = [len(t) for t in base_tokens]
# #     results = []

# #     while True:
# #         candidates = get_candidates(base_tokens)

# #         scored = [(loc, fuzzy_score(query, loc)) for loc in candidates]

# #         passed = [(loc, score) for loc, score in scored if score >= FUZZY_THRESHOLD]

# #         if passed:
# #             return sorted(passed, key=lambda x: -x[1])

# #         # Contract tokens
# #         all_at_min = all(len(t) <= MIN_TOKEN_LEN for t in base_tokens)
# #         if all_at_min:
# #             break

# #         for i in range(len(base_tokens)):
# #             if len(base_tokens[i]) > MIN_TOKEN_LEN:
# #                 base_tokens[i] = base_tokens[i][:-1]

# #     return []  # Nothing passed


# # # Debug CLI
# # if __name__ == "__main__":
# #     query = input("Query: ")
# #     for loc, score in search_localities(query)[:10]:
# #         print(
# #             f"{loc.name}, {loc.subdivision_name}, {loc.country_name} — Score: {score:.1f}"
# #         )

# import cProfile
# from villager.db import db


# cursor = db.execute_sql(
#     """
# WITH RECURSIVE subdivision_chain AS (
#     SELECT
#         s.id,
#         s.name,
#         s.category,
#         s.parent_id,
#         s.country_id,
#         s.id AS root_id,
#         0 AS depth
#     FROM subdivisions s

#     UNION ALL

#     SELECT
#         parent.id,
#         parent.name,
#         parent.category,
#         parent.parent_id,
#         child.country_id,
#         child.root_id,
#         depth + 1
#     FROM subdivisions parent
#     JOIN subdivision_chain child ON parent.id = child.parent_id
# )

# SELECT
#     l.id AS locality_id,
#     l.name AS locality_name,
#     l.lat,
#     l.lng,
#     l.classification,
#     l.osm_type,
#     l.osm_id,
#     l.population,
#     c.name AS country_name,
#     c.alpha2 AS country_alpha2,
#     c.alpha3 AS country_alpha3,
#     s.id AS subdivision_id,
#     s.name AS subdivision_name,
#     s.category AS subdivision_category,
# JOIN countries c ON l.country_id = c.id
# JOIN subdivision_chain sc ON l.subdivision_id = sc.root_id
# JOIN subdivisions s ON sc.id = s.id
# ORDER BY l.id, sc.depth ASC;

# """
# )

# from villager.types import Locality

# results = cursor.fetchall()

# for r in results:
#     print(r)
#     break


# # def run():
# #     for c in villager.countries:
# #         villager.countries.search(c.name + "g")


# # cProfile.run("run()")

# import villager
# from villager.db import db
from villager.db.dtos import Locality

import sqlite3

conn = sqlite3.connect("src/villager/db/villager.db")
cursor = conn.cursor()

cursor.execute(
    """SELECT l.*, 
      c.name as country_name, 
      c.alpha2, 
      c.alpha3,
      s1.name as subdivision_1_name, 
      s1.iso_code as subdivision_1_iso_code, 
      s1.code as sub1_code, 
      s1.category as sub1_category, 
      s1.admin_level as sub1_admin_level,
      s2.name as sub2_name, 
      s2.iso_code as sub2_iso_code, 
      s2.code as sub2_code, 
      s2.category as sub2_category, 
      s2.admin_level as sub2_admin_level,
      f.tokens
FROM localities l
JOIN subdivisions s1 ON l.subdivision_id = s1.id
JOIN countries c ON l.country_id = c.id
LEFT JOIN subdivisions s2 ON s1.parent_iso_code = s2.iso_code
JOIN localities_fts f ON l.id = f.rowid
WHERE f.tokens MATCH "madi*"
ORDER BY rank
LIMIT 1000;"""
)

cache = {}

for row in cursor.fetchall():
    l = Locality.from_row(row)
    id = row[0]
    cache[id] = l

    print(l.name)
