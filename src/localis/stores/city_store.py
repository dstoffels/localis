from array import array
from .store import Store


class CityStore(Store):
    __slots__ = (
        "geonames_ids",
        "subdivision_id_blob",
        "subdivision_offsets",
        "subdivision_counts",
        "country_ids",
        "populations",
        "lats",
        "lngs",
    )

    def __init__(self):
        super().__init__()
        self.geonames_ids = array("I")
        self.subdivision_id_blob = array("I")
        self.subdivision_offsets = array("I")
        self.subdivision_counts = array("B")
        self.country_ids = array("I")
        self.populations = array("I")
        self.lats = array("f")
        self.lngs = array("f")

    def append(
        self,
        name: str,
        geonames_id: int,
        subdivision_ids: list[int],
        country_id: int,
        population: int,
        lat: float,
        lng: float,
    ) -> None:
        self.names.append(name)
        self.geonames_ids.append(geonames_id)
        self.subdivision_offsets.append(len(self.subdivision_id_blob))
        self.subdivision_counts.append(len(subdivision_ids))
        self.subdivision_id_blob.extend(subdivision_ids)
        self.country_ids.append(country_id)
        self.populations.append(population)
        self.lats.append(lat)
        self.lngs.append(lng)
