from .model import Model
from .fields import CharField, IntField
from ..dtos import Country
from dataclasses import dataclass


class CountryModel(Model[Country]):
    table_name = "countries"
    dto_class = Country

    name = CharField()
    official_name = CharField()
    alpha2 = CharField()
    alpha3 = CharField()
    numeric = IntField()
    alt_names = CharField()
    flag = CharField(index=False)

    def to_dto(self):
        self.numeric = int(self.numeric) if self.numeric else None
        self.alt_names = self.alt_names.split("|") if self.alt_names else []
        return super().to_dto()

    def __init__(
        self,
        name: str,
        official_name: str,
        alpha2: str,
        alpha3: str,
        numeric: int,
        alt_names: str,
        flag: str,
        **kwargs
    ):
        self.name = name
        self.official_name = official_name
        self.alpha2 = alpha2
        self.alpha3 = alpha3
        self.numeric = numeric
        self.alt_names = alt_names
        self.flag = flag

        super().__init__(**kwargs)
