from pathlib import Path
from typing import Mapping
from localis.entities import CountryBase, SubdivisionBase, City
from localis.stores import CityStore
from .view import CrossReferencedView
from .country_view import CountryView
from .subdivision_view import SubdivisionView


class CityView(CrossReferencedView[City, CityStore, CountryView, SubdivisionView]):
    """Runtime view over CityStore, used by Registry._cache."""

    __slots__ = ()

    @property
    def name(self) -> str:
        return self._store.names[self._idx]

    @property
    def geonames_id(self) -> int:
        return self._store.geonames_ids[self._idx]

    @property
    def admin1(self) -> SubdivisionView | None:
        aid = self._store.admin1_ids[self._idx]
        return self._subdivision_views.get(aid) if aid != -1 else None

    @property
    def admin2(self) -> SubdivisionView | None:
        aid = self._store.admin2_ids[self._idx]
        return self._subdivision_views.get(aid) if aid != -1 else None

    @property
    def country(self) -> CountryView:
        country = self._country_views.get(self._store.country_ids[self._idx])
        assert country is not None, "city has no country, violates ingest invariant"
        return country

    @property
    def population(self) -> int:
        return self._store.populations[self._idx]

    @property
    def lat(self) -> float:
        return self._store.lats[self._idx]

    @property
    def lng(self) -> float:
        return self._store.lngs[self._idx]

    def to_entity(self) -> City:
        admin1 = self.admin1
        admin2 = self.admin2
        country = self.country
        return City(
            id=self.id,
            name=self.name,
            geonames_id=self.geonames_id,
            admin1=(
                SubdivisionBase(
                    id=admin1.id,
                    name=admin1.name,
                    geonames_code=admin1.geonames_code,
                    iso_code=admin1.iso_code,
                    type=admin1.type,
                )
                if admin1
                else None
            ),
            admin2=(
                SubdivisionBase(
                    id=admin2.id,
                    name=admin2.name,
                    geonames_code=admin2.geonames_code,
                    iso_code=admin2.iso_code,
                    type=admin2.type,
                )
                if admin2
                else None
            ),
            country=CountryBase(
                id=country.id,
                name=country.name,
                alpha2=country.alpha2,
                alpha3=country.alpha3,
            ),
            population=self.population,
            lat=self.lat,
            lng=self.lng,
        )

    @classmethod
    def load(
        cls,
        filepath: Path,
        country_views: Mapping[int, CountryView],
        subdivision_views: Mapping[int, SubdivisionView],
    ) -> dict[int, "CityView"]:
        store = CityStore()
        views: dict[int, CityView] = {}
        with open(filepath, "r", encoding="utf-8") as f:
            for id, line in enumerate(f, start=1):
                row = line.rstrip("\r\n").split("\t")
                (
                    name,
                    geonames_id_s,
                    admin1_s,
                    admin2_s,
                    country_s,
                    pop_s,
                    lat_s,
                    lng_s,
                ) = row
                geonames_id = int(geonames_id_s)
                admin1_id = int(admin1_s) if admin1_s else None
                admin2_id = int(admin2_s) if admin2_s else None
                country_id = int(country_s)
                population = int(pop_s)
                lat = float(lat_s)
                lng = float(lng_s)
                store.append(
                    name,
                    geonames_id,
                    admin1_id,
                    admin2_id,
                    country_id,
                    population,
                    lat,
                    lng,
                )
                views[id] = cls(id, store, country_views, subdivision_views)
        return views
