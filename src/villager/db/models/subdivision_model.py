from .model import (
    Model,
    AutoField,
    CharField,
    IntegerField,
    ForeignKeyField,
    Subdivision,
)
from .country_model import CountryModel
from villager.utils import normalize, tokenize


class SubdivisionModel(Model[Subdivision]):
    table_name = "subdivisions"
    dto_class = Subdivision
    fts_fields = ["name", "country", "country_code"]
    base_query = """SELECT
                    s.id as id,
                    s.name as name,
                    s.normalized_name as normalized_name,
                    s.iso_code as iso_code,
                    s.alt_name as alt_name,
                    s.code as code,
                    s.category as category,
                    s.parent_iso_code as parent_iso_code,
                    s.admin_level as admin_level,

                    c.name as country,
                    c.alpha2 as country_alpha2,
                    c.alpha3 as country_alpha3,

                    f.name as fts_name,
                    f.country as fts_country,
                    f.country_code as fts_country_code,
                    f.name || ' ' || f.country || ' ' || f.country_code as tokens

                    FROM subdivisions_fts f
                    JOIN subdivisions s ON f.rowid = s.id
                    JOIN countries c ON s.country_id = c.id
                    """

    id = AutoField()
    name = CharField(index=True, nullable=False)
    normalized_name = CharField(index=True, nullable=False)
    iso_code = CharField(unique=True)
    alt_name = CharField(index=True, nullable=True)
    code = CharField()
    category = CharField(index=True, nullable=True)
    parent_iso_code = CharField(index=True, nullable=True)
    admin_level = IntegerField(default=1)
    country_id: CountryModel = ForeignKeyField(references="countries")

    @classmethod
    def parse_raw(cls, raw_data):
        country_id, country, _, c_norm_name = CountryModel.get(
            CountryModel.alpha2 == raw_data["#country_code_alpha2"]
        )

        iso_code = raw_data["subdivision_code_iso3166-2"]
        name = raw_data["subdivision_name"]

        base = {
            "name": name,
            "normalized_name": normalize(name),
            "iso_code": iso_code,
            "code": iso_code.split("-")[-1] if "-" in iso_code else iso_code,
            "category": raw_data.get("category", None),
            "country_id": country_id,
            "alt_name": raw_data.get("localVariant", None),
            "parent_iso_code": raw_data.get("parent_subdivision"),
        }

        fts = {
            "name": normalize(name),
            "country": c_norm_name,
            "country_code": normalize(country.alpha2),
        }

        return base, fts
