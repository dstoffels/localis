from localis.entities import CountryLanguage, Language, LanguageBase, LanguageScript, ScriptBase
from ingest.utils import change_report


def _language(id: int, script_name: str, secondary: bool) -> Language:
    script = LanguageScript(id=id, name=script_name, alpha4="Latn", secondary=secondary)
    return Language(
        id=id, name="Demo", alpha3="dmo", alpha2=None, bibliographic=None, scope="individual", type="living",
        inverted_name=None, aliases=[], scripts=[script],
    )


class TestChangeReport:
    """CHANGE REPORT"""

    def test_compare(self):
        """should count both builds and list records added, removed and changed by key, with the fields that changed"""
        shipped = [("a", "A", {"x": 1}), ("b", "B", {"x": 1}), ("c", "C", {"x": 1, "y": 2})]
        staged = [("a", "A", {"x": 1}), ("c", "C", {"x": 1, "y": 3}), ("d", "D", {"x": 1})]

        result = change_report._compare(shipped, staged)

        assert result == (3, 3, ["`d` D"], ["`b` B"], ["`c` C: y"])

    def test_nested_base_as_key(self):
        """should reduce a nested record in its base form to its key"""
        assert change_report._nested(LanguageBase(id=1, name="Demo", alpha3="dmo", alpha2=None)) == "dmo"

    def test_nested_keeps_relationship_fields(self):
        """should keep the fields a nested record carries beyond its base form, its own nested records as keys"""
        language = CountryLanguage(
            id=1, name="Demo", alpha3="dmo", alpha2=None, status="official", population_percent=50.0,
            script=ScriptBase(id=1, name="Latin", alpha4="Latn"),
        )

        assert change_report._nested(language) == ("dmo", {"status": "official", "population_percent": 50.0, "script": "Latn"})

    def test_comparable_ignores_nested_record_changes(self):
        """should compare a record without its id or the names of its nested records, but with their relationship fields"""
        before = change_report._comparable(_language(1, "Latin", secondary=False))

        assert change_report._comparable(_language(2, "Roman", secondary=False)) == before
        assert change_report._comparable(_language(1, "Latin", secondary=True)) != before
