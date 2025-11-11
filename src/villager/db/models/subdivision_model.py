from .model import Model
from .fields import CharField
from ..dtos import Subdivision, SubdivisionBasic
from dataclasses import dataclass


class SubdivisionModel(Model[Subdivision]):
    table_name = "subdivisions"
    dto_class = Subdivision

    name = CharField()
    alt_names = CharField()
    type = CharField()
    geonames_code = CharField()
    iso_code = CharField()
    country = CharField()
    parent_id = CharField()

    def to_dto(self):
        sub = dict(self)
        sub["alt_names"] = self.alt_names.split("|")
        sub["parent_id"] = int(self.parent_id) if self.parent_id else None
        sub["admin_level"] = 2 if self.parent_id else 1

        return Subdivision(**sub)

    def __init__(
        self,
        name: str,
        alt_names: str,
        type: str,
        geonames_code: str,
        iso_code: str,
        country: str,
        parent_id: str,
        **extra
    ):
        self.name = name
        self.alt_names = alt_names
        self.type = type
        self.geonames_code = geonames_code
        self.iso_code = iso_code
        self.country = country
        self.parent_id = parent_id
