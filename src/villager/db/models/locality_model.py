from .model import (
    Model,
    AutoField,
    CharField,
    IntegerField,
    ForeignKeyField,
    FloatField,
    RowData,
)
from .country_model import CountryModel
from .subdivision_model import SubdivisionModel
from ..dtos import SubdivisionBasic, Locality
from villager.utils import normalize, tokenize, extract_iso_code, parse_other_names
import sqlite3


class LocalityModel(Model[Locality]):
    table_name = "localities"
    dto_class = Locality
    fts_fields = ["name", "subdivision", "country", "country_code"]
    base_query = """SELECT l.*, 
                    c.name as country, 
                    c.alpha2 as country_alpha2, 
                    c.alpha3 as country_alpha3,

                    s1.name as sub1_name, 
                    s1.iso_code as sub1_iso_code, 
                    s1.code as sub1_code, 
                    s1.category as sub1_category, 
                    s1.admin_level as sub1_admin_level,
                    s2.name as sub2_name, 
                    s2.iso_code as sub2_iso_code, 
                    s2.code as sub2_code, 
                    s2.category as sub2_category, 
                    s2.admin_level as sub2_admin_level,

                    f.name as fts_name,
                    f.subdivision as fts_subdivision,
                    f.country as fts_country,
                    f.country_code as fts_country_code,
                    f.name || ' ' || f.subdivision || ' ' || f.country || ' ' || f.country_code as tokens
                    
                FROM localities l
                JOIN subdivisions s1 ON l.subdivision_id = s1.id
                JOIN countries c ON l.country_id = c.id
                LEFT JOIN subdivisions s2 ON s1.parent_iso_code = s2.iso_code
                JOIN localities_fts f ON l.id = f.rowid
                """

    id = AutoField()
    name = CharField(index=True, nullable=False)
    normalized_name = CharField(index=True, nullable=False)
    classification = CharField()
    population = IntegerField(nullable=True)
    lat = FloatField()
    lng = FloatField()
    osm_id = IntegerField(index=True)
    osm_type = CharField(index=True)
    subdivision_id = ForeignKeyField(references="subdivisions")
    country_id = ForeignKeyField(references="countries")

    @classmethod
    def parse_raw(cls, raw_data) -> tuple[dict | None, dict | None]:
        # OSM
        osm_id = raw_data.get("osm_id")
        osm_type = raw_data.get("osm_type")

        if not osm_id or not osm_type:
            return None, None

        osm_type = osm_type[0]

        # Name
        name, other_names = parse_other_names(
            raw_data.get("name", None), raw_data.get("other_names", {})
        )
        if not name:
            return None, None

        # Address Data
        address: dict = raw_data.get("address", {})
        if not address:
            return None, None

        country_alpha2 = address.get("country_code")

        lng, lat = raw_data.get("location", (None, None))

        # Subdivision
        sub_iso_code = extract_iso_code(address)
        sub_data = SubdivisionModel.get(SubdivisionModel.iso_code == sub_iso_code)
        if not sub_data:
            return None, None
        subdivision_id, subdivision, _, sub_norm_name = sub_data

        # Country
        country_id, country, _, c_norm_name = CountryModel.get(
            CountryModel.alpha2 == country_alpha2
        )

        base = {
            "name": name,
            "normalized_name": normalize(name),
            "classification": raw_data["classification"],
            "population": raw_data.get("population", None),
            "lat": lat,
            "lng": lng,
            "osm_id": osm_id,
            "osm_type": osm_type,
            "country_id": country_id,
            "subdivision_id": subdivision_id,
        }

        fts = {
            "name": normalize(name),
            "subdivision": sub_norm_name,
            "country": c_norm_name,
            "country_code": normalize(country_alpha2),
        }

        return base, fts

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> RowData[Locality]:
        data = {k: row[k] for k in row.keys() if k in cls.dto_class.__annotations__}
        id = row["id"]
        tokens = row["tokens"]
        normalized_name = row["normalized_name"]

        subdivisions = []
        if row["sub1_name"]:
            subdivisions.append(
                SubdivisionBasic(
                    name=row["sub1_name"],
                    iso_code=row["sub1_iso_code"],
                    code=row["sub1_code"],
                    category=row["sub1_category"],
                    admin_level=row["sub1_admin_level"],
                )
            )

        if row["sub2_name"]:
            subdivisions.append(
                SubdivisionBasic(
                    name=row["sub2_name"],
                    iso_code=row["sub2_iso_code"],
                    code=row["sub2_code"],
                    category=row["sub2_category"],
                    admin_level=row["sub2_admin_level"],
                )
            )
        data["villager_id"] = f'{row["osm_type"]}:{row["osm_id"]}'
        data["subdivisions"] = subdivisions
        data["display_name"] = f'{row["name"]}, {row['sub1_name']}, {row["country"]}'
        return RowData(id, cls.dto_class(**data), tokens, normalized_name)
