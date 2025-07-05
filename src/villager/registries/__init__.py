from .country_registry import CountryRegistry
from .subdivision_registry import SubdivisionRegistry
from .locality_registry import LocalityRegistry
from ..db import db, CountryModel, SubdivisionModel, LocalityModel

countries = CountryRegistry(db, CountryModel)
subdivisions = SubdivisionRegistry(db, SubdivisionModel)
localities = LocalityRegistry(db, LocalityModel)
