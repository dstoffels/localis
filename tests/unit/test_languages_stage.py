import importlib
import pytest
from ingest.shared.models import LanguageModel, ScriptModel
from utils import write_json


class TestLanguageScripts:
    """LANGUAGE SCRIPTS"""

    @staticmethod
    def _scripts_of(monkeypatch, tmp_path, language_data: dict) -> list[tuple[str, bool]]:
        """The scripts _add_cldr_scripts() gives a language "dmo" (alpha2 "dm") from CLDR language data."""
        load_languages = importlib.import_module("ingest.languages.scripts.load_languages")
        write_json(tmp_path / "language_data.json", {"supplemental": {"languageData": language_data}})
        monkeypatch.setattr(load_languages, "CLDR_LANGUAGE_DATA_PATH", tmp_path / "language_data.json")
        language = LanguageModel(name="Demo", alpha3="dmo", alpha2="dm", bibliographic=None, scope="individual", type="living", inverted_name=None)
        scripts = {code: ScriptModel(name=code, alpha4=code, numeric=None) for code in ("Latn", "Cyrl")}

        load_languages._add_cldr_scripts({"dmo": language, "dm": language}, scripts)

        return [(s.script.alpha4, s.secondary) for s in language.scripts]

    def test_keeps_repeat_once(self, monkeypatch, tmp_path):
        """should keep a script CLDR lists twice for a language, under its alpha2 and alpha3, once"""
        data = {"dm": {"_scripts": ["Latn"]}, "dmo": {"_scripts": ["Latn", "Cyrl"]}}

        assert self._scripts_of(monkeypatch, tmp_path, data) == [("Latn", False), ("Cyrl", False)]

    def test_raises_on_primary_and_secondary(self, monkeypatch, tmp_path):
        """should raise on a script CLDR lists as both primary and secondary for a language, rather than keep either"""
        data = {"dmo": {"_scripts": ["Latn"]}, "dmo-alt-secondary": {"_scripts": ["Latn"]}}

        with pytest.raises(ValueError):
            self._scripts_of(monkeypatch, tmp_path, data)
