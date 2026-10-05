from pathlib import Path
from ingest.shared.models import (
    CityModel,
    CountryLanguageModel,
    CountryModel,
    CurrencyModel,
    HistoricModel,
    LanguageModel,
    LanguageScriptModel,
    MacroregionModel,
    ScriptModel,
    SubdivisionModel,
)
from ingest.utils.index import dump_data
from localis.views import CityView, CountryView, CurrencyView, LanguageView, MacroregionView, ScriptView, SubdivisionView


def _script(id: int) -> ScriptModel:
    return ScriptModel(id=id, name=f"Script {id}", alpha4=f"Sc{id:02d}", numeric=None)


def _language(id: int) -> LanguageModel:
    return LanguageModel(id=id, name=f"Language {id}", alpha3=f"l{id:02d}", alpha2=None, bibliographic=None, scope="individual", type="living", inverted_name=None)


def _macroregion(id: int) -> MacroregionModel:
    return MacroregionModel(id=id, name=f"Region {id}", code=f"{id:03d}", type="region", parent=None)


def _country(id: int) -> CountryModel:
    return CountryModel(id=id, name=f"Country {id}", alpha2="DM", alpha3=None, geonames_id=None, official_name=None, common_name=None, aliases=[], numeric=None, flag=None, historic=None)


def _subdivision(id: int, country: CountryModel, parent: SubdivisionModel | None = None) -> SubdivisionModel:
    return SubdivisionModel(id=id, name=f"Subdivision {id}", iso_code=None, geonames_code=f"DM.{id}", geonames_id=None, type=None, aliases=[], admin_level=1, parent=parent, country=country)


class TestRowFormats:
    """ROW FORMATS"""

    # each test writes a model whose every field holds a distinct value through ingest's dump, then reads it back through the runtime view, so a column the two order differently fails

    def test_macroregions(self, tmp_path: Path):
        """should read back every macroregion column, its parent included"""
        region = _macroregion(1)
        dump_data([region, MacroregionModel(id=2, name="Western Demo", code="155", type="subregion", parent=region)], tmp_path / "rows.tsv")

        view = MacroregionView.load(tmp_path / "rows.tsv")[2]

        assert (view.name, view.code, view.type) == ("Western Demo", "155", "subregion")
        assert view.parent is not None and view.parent.id == 1

    def test_currencies(self, tmp_path: Path):
        """should read back every currency column"""
        dump_data([CurrencyModel(id=1, name="Demo Dollar", alpha3="DMD", numeric=8)], tmp_path / "rows.tsv")

        view = CurrencyView.load(tmp_path / "rows.tsv")[1]

        assert (view.name, view.alpha3, view.numeric) == ("Demo Dollar", "DMD", 8)

    def test_scripts(self, tmp_path: Path):
        """should read back every script column"""
        dump_data([ScriptModel(id=1, name="Demoscript", alpha4="Dmos", numeric=999, aliases=["Demo A", "Demo B"])], tmp_path / "rows.tsv")

        view = ScriptView.load(tmp_path / "rows.tsv")[1]

        assert (view.name, view.alpha4, view.numeric, view.aliases) == ("Demoscript", "Dmos", 999, ("Demo A", "Demo B"))

    def test_languages(self, tmp_path: Path):
        """should read back every language column, primary and secondary scripts apart"""
        language = LanguageModel(
            id=1, name="Demolang", alpha3="dmo", alpha2="dm", bibliographic="dmb", scope="macrolanguage", type="historical", inverted_name="Lang, Demo",
            aliases=["Demoish"], scripts=[LanguageScriptModel(script=_script(3), secondary=False), LanguageScriptModel(script=_script(4), secondary=True)],
        )
        dump_data([language], tmp_path / "rows.tsv")

        view = LanguageView.load(tmp_path / "rows.tsv", {})[1]

        assert (view.name, view.alpha3, view.alpha2, view.bibliographic, view.scope, view.type, view.inverted_name, view.aliases) == (
            "Demolang", "dmo", "dm", "dmb", "macrolanguage", "historical", "Lang, Demo", ("Demoish",),
        )
        assert (view._store.script_ids[view._idx], view._store.secondary_script_ids[view._idx]) == ((3,), (4,))

    def test_countries(self, tmp_path: Path):
        """should read back every country column, its references as ids"""
        country = CountryModel(
            id=1, name="Demoland", alpha2="DM", alpha3="DMO", geonames_id=111, official_name="Republic of Demoland", common_name="Demo",
            aliases=["Demostan"], numeric=123, flag="🏳", historic=HistoricModel(alpha_4="DMHH", withdrawal_date="1990-01-01", comment="merged"),
            macroregions=[_macroregion(5), _macroregion(6)], groupings=[_macroregion(7)], currencies=[CurrencyModel(id=8, name="Demo Dollar", alpha3="DMD", numeric=None)],
            languages=[CountryLanguageModel(language=_language(9), status="regional", population_percent=12.5, script=_script(10))],
        )
        dump_data([country], tmp_path / "rows.tsv")

        view = CountryView.load(tmp_path / "rows.tsv", {}, {}, {}, {})[1]
        store, idx = view._store, view._idx

        assert (view.name, view.alpha2, view.alpha3, view.geonames_id, view.official_name, view.common_name, view.aliases, view.numeric, view.flag) == (
            "Demoland", "DM", "DMO", 111, "Republic of Demoland", "Demo", ("Demostan",), 123, "🏳",
        )
        assert view.historic is not None and (view.historic.alpha_4, view.historic.withdrawal_date, view.historic.comment) == ("DMHH", "1990-01-01", "merged")
        assert (store.macroregion_ids[idx], store.grouping_ids[idx], store.currency_ids[idx], store.languages[idx]) == ((5, 6), (7,), (8,), ((9, "regional", 12.5, 10),))

    def test_subdivisions(self, tmp_path: Path):
        """should read back every subdivision column, its parent and country as ids"""
        country = _country(3)
        parent = _subdivision(1, country)
        child = SubdivisionModel(id=2, name="Demo Province", iso_code="DM-B", geonames_code="DM.02", geonames_id=222, type="Province", aliases=["Demoshire"], admin_level=2, parent=parent, country=country)
        dump_data([parent, child], tmp_path / "rows.tsv")

        view = SubdivisionView.load(tmp_path / "rows.tsv", {})[2]

        assert (view.name, view.iso_code, view.geonames_code, view.geonames_id, view.type, view.aliases, view.admin_level) == (
            "Demo Province", "DM-B", "DM.02", 222, "Province", ("Demoshire",), 2,
        )
        assert view.parent is not None and view.parent.id == 1
        assert view._store.country_ids[view._idx] == 3

    def test_cities(self, tmp_path: Path):
        """should read back every city column, its subdivisions and country as ids"""
        country = _country(6)
        city = CityModel(id=1, name="Democity", geonames_id=333, subdivisions=[_subdivision(4, country), _subdivision(5, country)], country=country, population=7000, lat=1.5, lng=-2.25)
        dump_data([city], tmp_path / "rows.tsv")

        view = CityView.load(tmp_path / "rows.tsv", {}, {})[1]
        store, idx = view._store, view._idx
        offset, count = store.subdivision_offsets[idx], store.subdivision_counts[idx]

        assert (view.name, view.geonames_id, view.population, view.lat, view.lng) == ("Democity", 333, 7000, 1.5, -2.25)
        assert (list(store.subdivision_id_blob[offset : offset + count]), store.country_ids[idx]) == ([4, 5], 6)
