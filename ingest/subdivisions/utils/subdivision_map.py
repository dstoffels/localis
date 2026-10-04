from ingest.shared.models import SubdivisionModel


class SubdivisionMap:
    def __init__(self):
        self._subs: dict[str, dict[int, dict[int, SubdivisionModel]]] = {}
        self._by_id: dict[int, SubdivisionModel] = {}
        self._by_geo_code: dict[str, SubdivisionModel] = {}
        self._by_iso_code: dict[str, SubdivisionModel] = {}
        self._by_geonames_id: dict[int, SubdivisionModel] = {}

    def add(self, sub: SubdivisionModel) -> None:
        assert sub.hashid is not None, "subdivision must have hashid set before being added to the map"
        country_map = self._subs.setdefault(sub.country.alpha2, {})
        level_map = country_map.setdefault(sub.admin_level, {})
        level_map[sub.hashid] = sub
        self._by_id[sub.hashid] = sub
        if sub.iso_code:
            self._by_iso_code[sub.iso_code] = sub
        if sub.geonames_code:
            self._by_geo_code[sub.geonames_code] = sub
        if sub.geonames_id is not None:
            self._by_geonames_id[sub.geonames_id] = sub

    def get(
        self,
        id: int | None = None,
        geo_code: str | None = None,
        iso_code: str | None = None,
        geonames_id: int | None = None,
    ) -> SubdivisionModel | None:
        if id is not None:
            return self._by_id.get(id)
        if geo_code is not None:
            return self._by_geo_code.get(geo_code)
        if iso_code is not None:
            return self._by_iso_code.get(iso_code)
        if geonames_id is not None:
            return self._by_geonames_id.get(geonames_id)
        return None

    def filter(
        self, country_alpha2: str, admin_level: int | None = None
    ) -> list[SubdivisionModel]:
        """Filter subdivisions by country alpha2 code and optional admin level"""
        if admin_level is not None:
            return list(
                self._subs.get(country_alpha2, {}).get(admin_level, {}).values()
            )
        else:
            return [
                sub
                for level_map in self._subs.get(country_alpha2, {}).values()
                for sub in level_map.values()
            ]

    def all(self) -> list[SubdivisionModel]:
        """Returns a list of all subdivisions, assigning sequential IDs to each."""
        all = [
            sub
            for country_map in self._subs.values()
            for level_map in country_map.values()
            for sub in level_map.values()
        ]

        for id, sub in enumerate(all, start=1):
            sub.id = id

        return all

    def refresh(self) -> None:
        """Links every subdivision to its parent once merging has settled, then re-indexes the map under the final codes and levels."""
        subs = list(self._by_id.values())
        by_iso_code = {sub.iso_code: sub for sub in subs if sub.iso_code}
        by_geo_code = {sub.geonames_code: sub for sub in subs if sub.geonames_code}

        for sub in subs:
            # the parent comes from the source that owns the record: ISO's for a sub with an iso_code, otherwise the GeoNames code one level up
            if sub.iso_code is not None:
                sub.parent = by_iso_code.get(sub.parent_iso_code) if sub.parent_iso_code else None
            elif sub.geonames_code is not None and sub.geonames_code.count(".") == 2:
                sub.parent = by_geo_code.get(sub.geonames_code.rsplit(".", 1)[0])
            else:
                sub.parent = None

        for sub in subs:
            # a merged sub's admin_level is already ISO-authoritative; a pure GeoNames sub sits one below its parent, whose level is final either way (ISO-set if merged, 1 if not, since GeoNames never nests deeper)
            if sub.iso_code is None:
                sub.admin_level = sub.parent.admin_level + 1 if sub.parent else 1

        self._subs, self._by_geo_code, self._by_iso_code, self._by_geonames_id = {}, {}, {}, {}
        for sub in subs:
            self.add(sub)

    def __len__(self):
        return len(self._by_id)

    def to_geocode_map(self) -> dict[str, SubdivisionModel]:
        """Return a plain dict keyed by geonames_code, matching the shape load_subdivisions() reconstructs from disk."""
        return self._by_geo_code
