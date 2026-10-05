from ingest.utils import STAGED_DATA_PATH, ingest_log
from ingest.shared.models import CountryModel, HistoricModel


def load_countries() -> dict[str, CountryModel]:
    """The staged build's countries, for the resolve-subdivisions skill."""
    path = STAGED_DATA_PATH / "countries" / "countries.tsv"
    if not path.exists():
        raise FileNotFoundError(f"No staged countries at {path}; run the pipeline first")
    ingest_log.writeline("Loading staged countries...")
    columns = CountryModel.row_fields()
    countries: dict[str, CountryModel] = {}
    with open(path, "r", encoding="utf-8") as f:
        for id, line in enumerate(f, start=1):
            cells = line.rstrip("\n").split("\t")
            if len(cells) != len(columns):
                raise ValueError(f"{path} row {id} has {len(cells)} columns where CountryModel ships {len(columns)}; run the pipeline again to restage countries")
            row = dict(zip(columns, cells))
            # macroregion placements, currencies and languages are left out: downstream stages only relate to countries by id and name fields
            historic = HistoricModel.from_cell(row["historic"])
            # historic rows reuse active and each other's alpha2 codes, so key them by alpha_4 like ingest_countries() does
            key = historic.alpha_4 if historic else row["alpha2"]
            countries[key] = CountryModel(
                id=id,
                name=row["name"],
                alpha2=row["alpha2"],
                alpha3=row["alpha3"],
                geonames_id=int(row["geonames_id"]) if row["geonames_id"] else None,
                official_name=row["official_name"] or None,
                common_name=row["common_name"] or None,
                aliases=[a for a in row["aliases"].split("|") if a],
                numeric=int(row["numeric"]) if row["numeric"] else None,
                flag=row["flag"],
                historic=historic,
            )
    return countries
