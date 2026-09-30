from pathlib import Path
from typing import Mapping
from localis.entities import CountryBase, SubdivisionBase, Subdivision
from localis.stores import SubdivisionStore
from .view import CrossReferencedView
from .country_view import CountryView


class SubdivisionView(
    CrossReferencedView[Subdivision, SubdivisionStore, CountryView, "SubdivisionView"]
):
    """Runtime view over SubdivisionStore, used by Registry._cache."""

    __slots__ = ()

    @property
    def name(self) -> str:
        return self._store.names[self._idx]

    @property
    def geonames_code(self) -> str | None:
        v = self._store.geonames_codes[self._idx]
        return v if v else None

    @property
    def iso_code(self) -> str | None:
        v = self._store.iso_codes[self._idx]
        return v if v else None

    @property
    def type(self) -> str:
        return self._store.types[self._idx]

    @property
    def aliases(self) -> list[str]:
        return self._store.aliases[self._idx]

    @property
    def admin_level(self) -> int:
        return self._store.admin_levels[self._idx]

    @property
    def parent(self) -> "SubdivisionView | None":
        pid = self._store.parent_ids[self._idx]
        return self._subdivision_views.get(pid) if pid != -1 else None

    @property
    def country(self) -> CountryView:
        country = self._country_views.get(self._store.country_ids[self._idx])
        assert country is not None, "subdivision has no country, violates ingest invariant"
        return country

    @property
    def iso_suffix(self) -> str:
        return self.iso_code.split("-")[1] if self.iso_code else ""

    def to_entity(self) -> Subdivision:
        parent = self.parent
        country = self.country
        return Subdivision(
            id=self.id,
            name=self.name,
            geonames_code=self.geonames_code,
            iso_code=self.iso_code,
            type=self.type,
            aliases=self.aliases,
            admin_level=self.admin_level,
            parent=(
                SubdivisionBase(
                    id=parent.id,
                    name=parent.name,
                    geonames_code=parent.geonames_code,
                    iso_code=parent.iso_code,
                    type=parent.type,
                )
                if parent
                else None
            ),
            country=CountryBase(
                id=country.id,
                name=country.name,
                alpha2=country.alpha2,
                alpha3=country.alpha3,
            ),
        )

    @classmethod
    def load(
        cls, filepath: Path, country_views: Mapping[int, CountryView]
    ) -> dict[int, "SubdivisionView"]:
        store = SubdivisionStore()
        views: dict[int, SubdivisionView] = {}
        with open(filepath, "r", encoding="utf-8") as f:
            for id, line in enumerate(f, start=1):
                row = line.rstrip("\r\n").split("\t")
                (
                    name,
                    geonames_code,
                    iso_code,
                    type_,
                    alias_s,
                    admin_level_s,
                    parent_s,
                    country_s,
                ) = row
                alias_list = [a for a in alias_s.split("|") if a]
                admin_level = int(admin_level_s)
                parent_id = int(parent_s) if parent_s else None
                country_id = int(country_s)
                store.append(
                    name,
                    geonames_code,
                    iso_code,
                    type_,
                    alias_list,
                    admin_level,
                    parent_id,
                    country_id,
                )
                views[id] = cls(id, store, country_views, views)
        return views
