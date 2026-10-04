import csv
from ingest.utils import DATA_PATH, ingest_log
from ingest.shared.models import CountryModel, HistoricModel


def load_countries() -> dict[str, CountryModel]:
    ingest_log.writeline("Loading countries...")
    with open(DATA_PATH / "countries" / "countries.tsv", "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        countries: dict[str, CountryModel] = {}
        for id, row in enumerate(reader, start=1):
            # macroregion placements and currencies are left out: downstream stages only relate to countries by id and name fields
            name, alpha2, alpha3, geonames_id, official_name, common_name, aliases, numeric, flag, historic_cell, _, _, _ = row
            historic = HistoricModel.from_cell(historic_cell)
            # historic rows reuse active and each other's alpha2 codes, so key them by alpha_4 like ingest_countries() does
            key = historic.alpha_4 if historic else alpha2
            countries[key] = CountryModel(
                id=id,
                name=name,
                alpha2=alpha2,
                alpha3=alpha3,
                geonames_id=int(geonames_id) if geonames_id else None,
                official_name=official_name or None,
                common_name=common_name or None,
                aliases=[a for a in aliases.split("|") if a],
                numeric=int(numeric) if numeric else None,
                flag=flag,
                historic=historic,
            )
        return countries
