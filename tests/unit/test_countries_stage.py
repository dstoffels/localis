import importlib
import pytest
from utils import country_model, write_json


class TestCountries:
    """COUNTRIES"""

    def test_legal_tender_on_run_date(self):
        """should keep legal-tender currencies started by the run date and not yet ended, ending inclusive"""
        place_currencies = importlib.import_module("ingest.countries.scripts.place_currencies")
        entries = [
            {"NOW": {"_from": "2000-01-01"}},
            {"LTR": {"_from": "2026-11-01"}},
            {"OLD": {"_from": "1990-01-01", "_to": "2000-01-01"}},
            {"END": {"_from": "1990-01-01", "_to": "2026-10-05"}},
            {"FND": {"_from": "2000-01-01", "_tender": "false"}},
        ]

        assert place_currencies._legal_tender(country_model("DM", "DMO"), entries, "2026-10-05") == ["NOW", "END"]

    @pytest.mark.parametrize("short_names, aliases", [(["UAE"], ["UAE"]), ([], [])])
    def test_short_name_exempt_from_sports_codes(self, monkeypatch, tmp_path, short_names, aliases):
        """should keep a short name that's also the item's sports code, while dropping it as an alternative label"""
        merge_countries = importlib.import_module("ingest.countries.scripts.merge_countries")
        write_json(tmp_path / "blocklist.json", {})
        monkeypatch.setattr(merge_countries, "NAME_BLOCKLIST_PATH", tmp_path / "blocklist.json")
        countries = {"AE": country_model("AE", "ARE")}

        merge_countries.merge_wikidata(countries, {"AE": {"names": ["UAE"], "short_names": short_names, "codes": ["UAE"]}})

        assert countries["AE"].aliases == aliases

    def test_parse_continents(self):
        """should read the readme's continent lines, ignoring the rest, and refuse a readme without exactly seven distinct codes"""
        merge_countries = importlib.import_module("ingest.countries.scripts.merge_countries")
        codes = ["AF", "AS", "EU", "NA", "OC", "SA", "AN"]
        lines = [f"{code} : Continent {code}\t\t\tgeonameId={6255146 + i}" for i, code in enumerate(codes)]
        readme = "\n".join(["Continent codes :", *lines, "", "feature classes:", "A: country, state, region,..."])

        continents = merge_countries.parse_continents(readme)

        assert list(continents) == codes
        assert (continents["EU"].name, continents["EU"].geonames_code, continents["EU"].geonames_id) == ("Continent EU", "EU", 6255148)
        for broken in (lines[:-1], [*lines, lines[0]]):
            with pytest.raises(ValueError):
                merge_countries.parse_continents("\n".join(broken))
