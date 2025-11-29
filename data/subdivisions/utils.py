from data.utils import (
    CountryData,
    SubdivisionData,
    FIXTURE_PATH,
    generate_trigrams,
    normalize,
)
import csv


class SubdivisionMap:
    def __init__(self):
        self._subs: dict[str, dict[int, dict[int, SubdivisionData]]] = {}
        self._by_id: dict[int, SubdivisionData] = {}
        self._by_geo_code: dict[str, SubdivisionData] = {}
        self._by_iso_code: dict[str, SubdivisionData] = {}

    def add(self, sub: SubdivisionData) -> None:
        country_map = self._subs.setdefault(sub.country_alpha2, {})
        level_map = country_map.setdefault(sub.admin_level, {})
        level_map[sub.id] = sub
        self._by_id[sub.id] = sub
        if sub.iso_code:
            self._by_iso_code[sub.iso_code] = sub
        if sub.geonames_code:
            self._by_geo_code[sub.geonames_code] = sub

    def get(
        self, id: int = None, geo_code: str = None, iso_code: str = None
    ) -> SubdivisionData:
        if id is not None:
            return self._by_id.get(id)
        if geo_code is not None:
            return self._by_geo_code.get(geo_code)
        if iso_code is not None:
            return self._by_iso_code.get(iso_code)

    def filter(
        self, country_alpha2: str, admin_level: int = None
    ) -> list[SubdivisionData]:
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

    def all(self) -> SubdivisionData:
        return [
            sub
            for country_map in self._subs.values()
            for level_map in country_map.values()
            for sub in level_map.values()
        ]

    def refresh(self):
        self._subs, self._by_geo_code, self._by_iso_code = {}, {}, {}
        for sub in self._by_id.values():
            self.add(sub)
            if sub.parent_code and not sub.parent_id:
                if "-" in sub.parent_code:
                    sub.parent_id = self._by_iso_code[sub.parent_code].id
                elif "." in sub.parent_code:
                    sub.parent_id = self._by_geo_code[sub.parent_code].id

    def get_final(self) -> list[SubdivisionData]:
        """Returns an ordered list of all subdivisions to align the rowid to all parent ids for db normalization"""
        all_subs: list[SubdivisionData] = sorted(
            self.all(), key=lambda s: (s.country_alpha2, s.admin_level, s.name)
        )

        id_map = {sub.id: i for i, sub in enumerate(all_subs, start=1)}

        for sub in all_subs:
            sub.id = id_map[sub.id]
            sub.parent_id = id_map.get(sub.parent_id)
            sub.search_tokens = "|".join(set(generate_trigrams(normalize(sub.name))))

        return all_subs

    def __len__(self):
        return len(self._by_id)


def load_countries() -> dict[str, CountryData]:
    print("Loading countries...")
    with open(FIXTURE_PATH / "countries.tsv", "r", encoding="utf-8") as f:
        csv_reader = csv.DictReader(f, delimiter="\t")
        return {
            row["alpha2"]: CountryData(
                id=id,
                name=row["name"],
                official_name=row["official_name"],
                alpha2=row["alpha2"],
                alpha3=row["alpha3"],
                numeric=row["numeric"],
                alt_names=row["alt_names"].split("|") if row["alt_names"] else [],
                flag=row["flag"],
            )
            for id, row in enumerate(csv_reader, 1)
        }


def dedupe(items: list[str]) -> list[str]:
    seen = {}
    for s in items:
        key = s.lower()
        if key not in seen or len(s) < len(seen[key]):
            seen[key] = s
    return sorted(seen.values())


def is_iso_code(code: str) -> bool:
    return "-" in code
