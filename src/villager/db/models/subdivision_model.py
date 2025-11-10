from .model import (
    Model,
    AutoField,
    CharField,
    IntegerField,
    ForeignKeyField,
    Subdivision,
    SubdivisionBasic,
)
from .country_model import CountryModel
from villager.utils import normalize, tokenize


class SubdivisionModel(Model[Subdivision]):
    table_name = "subdivisions"
    dto_class = Subdivision

    name = CharField()
    alt_names = CharField()
    type = CharField(index=False)
    geonames_code = CharField()
    iso_code = CharField()
    country = CharField()
    parent_rowid = CharField()

    @classmethod
    def from_row(cls, row):
        row = dict(row)

        print(row)
        exit()

        row["iso_code"] = f'{row["country_alpha2"]}-{row["code"]}'

        subs = SubdivisionModel.select(SubdivisionModel.parent_rowid == row["iso_code"])
        row["subdivisions"] = []
        for s in subs:
            row["subdivisions"].append(
                SubdivisionBasic(name=s.name, code=s.code, admin_level=s.admin_level)
            )

        row["aliases"] = [a for a in row["aliases"].split("|")]
        return super().from_row(row)

    @classmethod
    def get_by_iso_code(cls, iso_code: str) -> Subdivision:
        alpha2, *code = tuple(iso_code.split("-"))
        code = "-".join([*code])
        return cls.get((cls.country_alpha2 == alpha2) & (cls.geonames_code == code))
