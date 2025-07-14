from .model import Model, AutoField, CharField, IntegerField, Country
from villager.utils import normalize, tokenize


class CountryModel(Model[Country]):
    table_name = "countries"
    dto_class = Country
    fts_fields = ["name", "alpha2", "alpha3"]
    query_select: str = """SELECT 
                    c.*, 
                    
                    matched.name as fts_name,
                    matched.alpha2 as fts_alpha2,
                    matched.alpha3 as fts_alpha3,

                    matched.name || ' ' || 
                    matched.alpha2 || ' ' || 
                    matched.alpha3 
                    as tokens
                    """
    query_tables: list[str] = [
        "FROM countries_fts matched",
        "JOIN countries c ON matched.rowid = c.id",
    ]

    id = AutoField()
    name = CharField(index=True, nullable=False)
    normalized_name = CharField(index=True, nullable=False)
    alpha2 = CharField(unique=True, index=True)
    alpha3 = CharField(unique=True, index=True)
    numeric = IntegerField(unique=True)
    long_name = CharField()

    @classmethod
    def parse_raw(cls, raw_data):
        norm_name = normalize(raw_data["name_short"])
        alpha2 = raw_data["#country_code_alpha2"]
        alpha3 = raw_data["country_code_alpha3"]
        base = {
            "name": raw_data["name_short"],
            "normalized_name": norm_name,
            "alpha2": alpha2,
            "alpha3": alpha3,
            "numeric": int(raw_data["numeric_code"]),
            "long_name": raw_data["name_long"],
        }

        fts = {
            "name": norm_name,
            "alpha2": normalize(alpha2),
            "alpha3": normalize(alpha3),
        }
        return base, fts
