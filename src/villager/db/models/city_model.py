from .model import Model
from .fields import CharField, IntField, FloatField
from ..dtos import SubdivisionBasic, City
from dataclasses import dataclass


class CityModel(Model[City]):
    table_name = "cities"
    dto_class = City

    name = CharField()
    geonames_id = CharField()
    admin1 = CharField()
    admin2 = CharField()
    country = CharField()
    alt_names = CharField()
    population = IntField(index=False)
    lat = FloatField(index=False)
    lng = FloatField(index=False)

    def to_dto(self) -> City:

        def parse_subdivision(raw_sub: str | None, lvl: int) -> SubdivisionBasic | None:
            if raw_sub is not None:
                name, geonames_code, iso_code = raw_sub.split("|")
                return SubdivisionBasic(name, geonames_code, iso_code, lvl)

        # build subdivision DTOs
        admin1 = parse_subdivision(self.admin1, 1)
        admin2 = parse_subdivision(self.admin2, 2)
        subdivisions = [s for s in (admin1, admin2) if s is not None]

        # parse country
        country_parts = self.country.split("|")
        country = country_parts[0]
        alpha2 = country_parts[1] if len(country_parts) > 1 else None
        alpha3 = country_parts[2] if len(country_parts) > 2 else None

        # build display name
        display_parts = [self.name, *[s.name for s in subdivisions[::-1]], country]
        display_name = ", ".join(display_parts)

        return City(
            id=self.id,
            geonames_id=int(self.geonames_id),
            name=self.name,
            display_name=display_name,
            subdivisions=subdivisions,
            country=country,
            country_alpha2=alpha2,
            country_alpha3=alpha3,
            alt_names=self.alt_names.split("|"),
            population=int(self.population),
            lat=float(self.lat),
            lng=float(self.lng),
        )

    def __init__(
        self,
        geonames_id: int,
        name: str,
        admin1: str,
        admin2: str,
        country: str,
        alt_names: str,
        population: int,
        lat: float,
        lng: float,
        **kwargs
    ):
        self.geonames_id = geonames_id
        self.name = name
        self.admin1 = admin1
        self.admin2 = admin2
        self.country = country
        self.alt_names = alt_names or ""
        self.population = population
        self.lat = lat
        self.lng = lng

        super().__init__(**kwargs)
