import sys
from pathlib import Path
from typing import Mapping
from localis.entities import SubdivisionBase, Subdivision
from localis.stores import SubdivisionStore
from .view import CrossReferencedView, ViewMap
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
    def geonames_id(self) -> int | None:
        v = self._store.geonames_ids[self._idx]
        return v if v != -1 else None

    @property
    def iso_code(self) -> str | None:
        v = self._store.iso_codes[self._idx]
        return v if v else None

    @property
    def type(self) -> str | None:
        v = self._store.types[self._idx]
        return v if v else None

    @property
    def aliases(self) -> tuple[str, ...]:
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
        return self._country_views[self._store.country_ids[self._idx]]

    @property
    def iso_suffix(self) -> str:
        return self.iso_code.split("-")[1] if self.iso_code else ""

    def to_base(self) -> SubdivisionBase:
        return SubdivisionBase(
            id=self.id,
            name=self.name,
            geonames_code=self.geonames_code,
            geonames_id=self.geonames_id,
            iso_code=self.iso_code,
            type=self.type,
            admin_level=self.admin_level,
        )

    def to_entity(self) -> Subdivision:
        parent = self.parent
        return Subdivision(
            id=self.id,
            name=self.name,
            geonames_code=self.geonames_code,
            geonames_id=self.geonames_id,
            iso_code=self.iso_code,
            type=self.type,
            admin_level=self.admin_level,
            aliases=list(self.aliases),
            parent=parent.to_base() if parent else None,
            country=self.country.to_base(),
        )

    @classmethod
    def load(
        cls, filepath: Path, country_views: Mapping[int, CountryView]
    ) -> ViewMap["SubdivisionView"]:
        store = SubdivisionStore()
        with open(filepath, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                row = line.rstrip("\r\n").split("\t")
                (
                    name,
                    iso_code,
                    geonames_code,
                    geonames_id_s,
                    type_,
                    alias_s,
                    admin_level_s,
                    parent_s,
                    country_s,
                ) = row
                alias_list = tuple(a for a in alias_s.split("|") if a)
                geonames_id = int(geonames_id_s) if geonames_id_s else None
                admin_level = int(admin_level_s)
                parent_id = int(parent_s) if parent_s else None
                country_id = int(country_s)
                store.id_to_idx.append(idx)
                store.append(
                    name,
                    geonames_code,
                    geonames_id,
                    iso_code,
                    # interned, since about a hundred ISO types repeat across the rows
                    sys.intern(type_),
                    alias_list,
                    admin_level,
                    parent_id,
                    country_id,
                )
        # a subdivision's parent resolves against this same mapping
        views: ViewMap[SubdivisionView] = ViewMap(store, lambda id: cls(id, store, country_views, views))
        return views
