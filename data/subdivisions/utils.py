from data.utils import DATA_PATH
import csv
import gzip
from localis.models import CountryModel, SubdivisionModel


class SubdivisionMap:
    def __init__(self):
        self._subs: dict[str, dict[int, dict[int, SubdivisionModel]]] = {}
        self._by_id: dict[int, SubdivisionModel] = {}
        self._by_geo_code: dict[str, SubdivisionModel] = {}
        self._by_iso_code: dict[str, SubdivisionModel] = {}

    def add(self, sub: SubdivisionModel) -> None:
        country_map = self._subs.setdefault(sub.country.alpha2, {})
        level_map = country_map.setdefault(sub.admin_level, {})
        level_map[sub.hashid] = sub
        self._by_id[sub.hashid] = sub
        if sub.iso_code:
            self._by_iso_code[sub.iso_code] = sub
        if sub.geonames_code:
            self._by_geo_code[sub.geonames_code] = sub

    def get(
        self, id: int = None, geo_code: str = None, iso_code: str = None
    ) -> SubdivisionModel:
        if id is not None:
            return self._by_id.get(id)
        if geo_code is not None:
            return self._by_geo_code.get(geo_code)
        if iso_code is not None:
            return self._by_iso_code.get(iso_code)
        return None

    def filter(
        self, country_alpha2: str, admin_level: int = None
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

    def refresh(self):
        self._subs, self._by_geo_code, self._by_iso_code = {}, {}, {}
        for sub in self._by_id.values():
            sub.admin_level = 2 if sub.parent else 1
            self.add(sub)

    def __len__(self):
        return len(self._by_id)


def dedupe(items: list[str]) -> list[str]:
    seen = {}
    for s in items:
        key = s.lower()
        if key not in seen or len(s) < len(seen[key]):
            seen[key] = s
    return sorted(seen.values())


def is_iso_code(code: str) -> bool:
    return "-" in code
