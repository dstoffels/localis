from localis.data.models.model import Model
from localis.data.models.fields import CharField, CompoundField
from localis.dtos import Subdivision


class SubdivisionModel(Model[Subdivision]):
    table_name = "subdivisions"
    dto_class = Subdivision

    name = CharField()
    alt_names = CharField()
    type = CharField()
    geonames_code = CharField()
    iso_code = CharField()
    country = CompoundField()
    parent_id = CharField()

    def to_dto(self):
        self.alt_names = self.alt_names.split("|") if self.alt_names else []
        self.parent_id = int(self.parent_id) if self.parent_id else None
        self.admin_level = 2 if self.parent_id else 1
        self.country, self.country_alpha2, self.country_alpha3 = self.country.split("|")
        return super().to_dto()

    def __init__(
        self,
        name: str,
        alt_names: str,
        type: str,
        geonames_code: str,
        iso_code: str,
        country: str,
        parent_id: str,
        **kwargs,
    ):
        self.name = name
        self.alt_names = alt_names or ""
        self.type = type
        self.geonames_code = geonames_code
        self.iso_code = iso_code
        self.country = country
        self.parent_id = parent_id

        super().__init__(**kwargs)
