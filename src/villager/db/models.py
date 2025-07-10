from peewee import (
    Model,
    CharField,
    IntegerField,
    AutoField,
    Select,
    FloatField,
    ForeignKeyField,
)
from .database import db
from abc import abstractmethod
from ..types import Country, Subdivision, Locality
from typing import TypeVar, Generic
from playhouse.sqlite_ext import FTS5Model, SearchField


T = TypeVar("T")


class DTOModel(Generic[T]):
    id = AutoField()

    def to_dto(self) -> T:
        raise NotImplementedError

    @classmethod
    def select(cls, *fields) -> Select:
        return super().select(*fields)

    @classmethod
    def to_dtos(cls) -> list[T]:
        return [row.to_dto() for row in cls.select().iterator()]


class BaseModel(Model):
    name = CharField(index=True)
    normalized_name = CharField(index=True)

    class Meta:
        database = db


class FTSBase(FTS5Model):
    tokens = SearchField()

    class Meta:
        database = db
        options = {
            "tokenize": "porter",
            "content_rowid": "id",
        }


class CountryModel(BaseModel, DTOModel[Country]):
    alpha2 = CharField(unique=True, max_length=2)
    alpha3 = CharField(unique=True, max_length=3)
    numeric = IntegerField(unique=True)
    long_name = CharField()

    def to_dto(self):
        return Country(
            id=self.id,
            name=self.name,
            alpha2=self.alpha2,
            alpha3=self.alpha3,
            numeric=self.numeric,
            long_name=self.long_name,
        )

    class Meta:
        table_name = "countries"


class CountryFTS(FTSBase):
    class Meta:
        table_name = "countries_fts"


class SubdivisionModel(BaseModel, DTOModel[Subdivision]):
    iso_code = CharField(unique=True)
    alt_name = CharField(index=True, null=True)
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
            id=self.id,
            name=self.name,
            alt_name=self.alt_name,
            iso_code=self.iso_code,
            code=self.code,
            admin_level=self.admin_level,
            category=self.category,
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


class SubdivisionFTS(FTSBase):
    class Meta:
        table_name = "subdivisions_fts"


class LocalityModel(BaseModel, DTOModel[Locality]):
    osm_id = IntegerField(index=True)
    osm_type = CharField(index=True, max_length=1)
    subdivision: SubdivisionModel = ForeignKeyField(
        SubdivisionModel, backref="localities"
    )
    country: CountryModel = ForeignKeyField(CountryModel, backref="localities")
    lat = FloatField()
    lng = FloatField()
    classification = CharField(max_length=1)
    population = IntegerField(null=True)

    def to_dto(self):
        subdivisions_chain = [sub.to_dto() for sub in self.subdivision.get_ancestors()]
        return Locality(
            osm_id=self.osm_id,
            osm_type=self.osm_type,
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
            population=self.population,
        )

    class Meta:
        table_name = "localities"


class LocalityFTS(FTSBase):
    class Meta:
        table_name = "localities_fts"
