from pathlib import Path
from typing import Mapping
from localis.entities import City
from localis.stores import CityStore
from localis.utils.data import CacheFilterPredicate
from .view import CrossReferencedView, ViewMap
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
    def subdivisions(self) -> list[SubdivisionView]:
        offset = self._store.subdivision_offsets[self._idx]
        count = self._store.subdivision_counts[self._idx]
        blob = self._store.subdivision_id_blob
        return [self._subdivision_views[sid] for sid in blob[offset : offset + count]]

    @property
    def country(self) -> CountryView:
        return self._country_views[self._store.country_ids[self._idx]]

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
        return City(
            id=self.id,
            name=self.name,
            geonames_id=self.geonames_id,
            subdivisions=[s.to_base() for s in self.subdivisions],
            country=self.country.to_base(),
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
        predicate: CacheFilterPredicate | None = None,
    ) -> ViewMap["CityView"]:
        store = CityStore()
        idx = 0

        with open(filepath, "r", encoding="utf-8") as f:
            for id, line in enumerate(f, start=1):

                row = line.rstrip("\r\n").split("\t")

                if predicate and not predicate(row):
                    store.id_to_idx.append(-1)
                    continue
                (
                    name,
                    geonames_id,
                    subdivisions,
                    country,
                    pop,
                    lat,
                    lng,
                ) = row
                store.id_to_idx.append(idx)
                store.append(
                    name,
                    int(geonames_id),
                    [int(sid) for sid in subdivisions.split("|") if sid],
                    int(country),
                    int(pop),
                    float(lat),
                    float(lng),
                )
                idx += 1
        return ViewMap(store, lambda id: cls(id, store, country_views, subdivision_views))
