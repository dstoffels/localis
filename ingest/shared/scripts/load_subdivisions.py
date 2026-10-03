from ingest.utils import DATA_PATH, ingest_log
from ingest.shared.models import CountryModel, SubdivisionModel
import csv


def load_subdivisions(
    countries: dict[str, CountryModel],
) -> dict[str, SubdivisionModel]:
    """Reconstructs subdivisions from the shipped dataset, keyed by geonames_code to match SubdivisionMap.to_geocode_map()'s shape. Parents are resolved in a second pass since a subdivision's parent row may not be loaded yet."""
    ingest_log.writeline("Loading Subdivisions...")
    countries_by_id: dict[int, CountryModel] = {c.id: c for c in countries.values()}

    subdivisions: dict[str, SubdivisionModel] = {}
    by_id: dict[int, SubdivisionModel] = {}
    pending_parents: dict[int, int] = {}

    with open(
        DATA_PATH / "subdivisions" / "subdivisions.tsv", "r", encoding="utf-8"
    ) as f:
        reader = csv.reader(f, delimiter="\t")
        for id, row in enumerate(reader, start=1):
            name, iso_code, geonames_code, geonames_id, type_, aliases, admin_level, parent, country_id = row

            subdivision = SubdivisionModel(
                id=id,
                name=name,
                iso_code=iso_code or None,
                geonames_code=geonames_code or None,
                geonames_id=int(geonames_id) if geonames_id else None,
                type=type_ or None,
                aliases=[a for a in aliases.split("|") if a],
                admin_level=int(admin_level),
                parent=None,
                country=countries_by_id[int(country_id)],
            )

            if parent:
                pending_parents[id] = int(parent)

            by_id[id] = subdivision
            if geonames_code:
                subdivisions[geonames_code] = subdivision

    for id, parent_id in pending_parents.items():
        by_id[id].parent = by_id.get(parent_id)

    return subdivisions
