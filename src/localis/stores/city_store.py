from array import array
from .store import Store


class CityStore(Store):
    __slots__ = (
        "geonames_ids",
        "admin1_ids",
        "admin2_ids",
        "country_ids",
        "populations",
        "lats",
        "lngs",
    )

    def __init__(self):
        super().__init__()
        self.geonames_ids = array("I")
        self.admin1_ids = array("i")  # -1 sentinel for None
        self.admin2_ids = array("i")  # -1 sentinel for None
        self.country_ids = array("I")
        self.populations = array("I")
        self.lats = array("f")
        self.lngs = array("f")

    def append(
        self,
        name: str,
        geonames_id: int,
        admin1_id: int | None,
        admin2_id: int | None,
        country_id: int,
        population: int,
        lat: float,
        lng: float,
    ) -> None:
        self.names.append(name)
        self.geonames_ids.append(geonames_id)
        self.admin1_ids.append(admin1_id if admin1_id is not None else -1)
        self.admin2_ids.append(admin2_id if admin2_id is not None else -1)
        self.country_ids.append(country_id)
        self.populations.append(population)
        self.lats.append(lat)
        self.lngs.append(lng)
