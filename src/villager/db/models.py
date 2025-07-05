from peewee import (
    Model,
    CharField,
    IntegerField,
    AutoField,
    Select,
    FloatField,
    ForeignKeyField,
    TextField,
)
from .database import db
from abc import abstractmethod
from ..types import Country, Subdivision, Locality
from typing import TypeVar, Generic
from playhouse.sqlite_ext import FTS5Model, SearchField


T = TypeVar("T")


class DTOModel(Generic[T]):
    def to_dto(self) -> T:
        raise NotImplementedError

    @classmethod
    def select(cls, *fields) -> Select:
        return super().select(*fields)

    @classmethod
    def to_dtos(cls) -> list[T]:
        return [row.to_dto() for row in cls.select().iterator()]


class BaseModel(Model):
    class Meta:
        database = db


class CountryModel(BaseModel, DTOModel[Country]):
    id = AutoField()
    name = CharField(index=True)
    alpha2 = CharField(unique=True, max_length=2)
    alpha3 = CharField(unique=True, max_length=3)
    numeric = IntegerField(unique=True)
    long_name = CharField()

    def to_dto(self):
        return Country(
            self.name,
            self.alpha2,
            self.alpha3,
            self.numeric,
            self.long_name,
        )

    class Meta:
        table_name = "countries"


class SubdivisionModel(BaseModel, DTOModel[Subdivision]):
    id = AutoField()
    name = CharField(index=True)
    alt_name = CharField(index=True, null=True)
    iso_code = CharField(unique=True)
    code = CharField(index=True)
    category = CharField(index=True, null=True)
    parent_iso_code = CharField(index=True, null=True)
    parent: "SubdivisionModel" = ForeignKeyField(
        "self", backref="subdivisions", null=True
    )
    admin_level = IntegerField(index=True, default=1)
    country: CountryModel = ForeignKeyField(CountryModel, backref="subdivisions")

    subdivisions: list["SubdivisionModel"]

    def to_dto(self) -> Subdivision:
        return Subdivision(
            name=self.name,
            alt_name=self.alt_name,
            iso_code=self.iso_code,
            code=self.code,
            category=self.category,
            # subdivisions=[child.to_dto() for child in self.subdivisions],
            country=self.country.name,
            country_alpha2=self.country.alpha2,
            country_alpha3=self.country.alpha3,
        )

    def get_ancestors(self) -> list["SubdivisionModel"]:
        """Return list of subdivisions from top-level parent down to self."""
        ancestors = []
        current = self
        while current:
            ancestors.append(current)
            current = current.parent
        return list(reversed(ancestors))

    class Meta:
        table_name = "subdivisions"


class LocalityModel(BaseModel, DTOModel[Locality]):
    id = AutoField()
    name = CharField(index=True)
    subdivision: SubdivisionModel = ForeignKeyField(
        SubdivisionModel, backref="localities"
    )
    country: CountryModel = ForeignKeyField(CountryModel, backref="localities")
    lat = FloatField()
    lng = FloatField()
    classification = CharField()
    osm_type = CharField()
    osm_id = IntegerField()
    population = IntegerField(null=True)

    def to_dto(self):
        subdivisions_chain = [sub.to_dto() for sub in self.subdivision.get_ancestors()]
        return Locality(
            name=self.name,
            subdivisions=subdivisions_chain,
            country=self.country.name,
            country_alpha2=self.country.alpha2,
            country_alpha3=self.country.alpha3,
            display_name=", ".join(
                [self.name]
                + [sub.name for sub in subdivisions_chain]
                + [self.country.name]
            ),
            lat=self.lat,
            lng=self.lng,
            classification=self.classification,
            osm_type=self.osm_type,
            osm_id=self.osm_id,
            population=self.population,
        )

    class Meta:
        table_name = "localities"


class LocalityFTS(FTS5Model):
    full_text = SearchField()

    class Meta:
        extension_options = {
            "tokenize": "porter",
            "content_rowid": "id",
            "prefix": "2 3 4 5 6 7 8 9",
        }
        content = "localities"
        database = db
