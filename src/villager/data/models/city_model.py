from villager.data.models.model import Model
from villager.data.models.fields import CharField, IntField, FloatField
from villager.dtos import SubdivisionBasic, City
from villager.utils import clean_row, chunked
import csv


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
            if raw_sub:
                name, geonames_code, iso_code = raw_sub.split("|")
                return SubdivisionBasic(name, geonames_code, iso_code, lvl)

        # build subdivision DTOs
        admin1 = parse_subdivision(self.admin1, 1)
        admin2 = parse_subdivision(self.admin2, 2)
        subdivisions = [s for s in (admin1, admin2) if s is not None]

        # parse country
        country_parts = self.country.split("|")
        country = country_parts[0] if country_parts else None
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
            alt_names=self.alt_names.split("|") if self.alt_names else [],
            population=int(self.population),
            lat=float(self.lat),
            lng=float(self.lng),
        )

    @classmethod
    def load(cls, file):
        cls.db.create_tables([CityModel])
        cities: list[dict] = []
        reader = csv.DictReader(file, delimiter="\t")

        for row in reader:
            MAX_DIGITS = 9
            row["population"] = f"{int(row['population']):0{MAX_DIGITS}d}"
            cities.append(clean_row(row))

        with cls.db.atomic():
            for batch in chunked(list(cities), 1000):
                try:
                    cls.insert_many(batch)
                except Exception as e:
                    print(f"Unexpected error on batch: {e}")
                    raise e

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
        **kwargs,
    ):
        self.geonames_id = geonames_id
        self.name = name
        self.admin1 = admin1 or ""
        self.admin2 = admin2 or ""
        self.country = country or ""
        self.alt_names = alt_names or ""
        self.population = population
        self.lat = lat
        self.lng = lng

        super().__init__(**kwargs)
