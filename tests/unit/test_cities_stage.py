import importlib
import pytest
from ingest.shared.models import SubdivisionModel
from ingest.utils import paths
from utils import country_model


class TestCities:
    """CITIES"""

    @staticmethod
    def _row(geonameid: int, admin1: str, admin2: str = "") -> str:
        cells = [str(geonameid), "Demo", "Demo", "", "1.0", "2.0", "P", "PPL", "DM", "", admin1, admin2, "", "", "600", "", "", "", ""]
        return "\t".join(cells) + "\n"

    def test_counts_unlinked_cities(self, repo):
        """should link a city through its admin codes and count each unlinked one by why"""
        load_cities = importlib.import_module("ingest.cities.scripts.load_cities")
        path = paths.Stage("cities").inputs / "cities500.txt"
        path.parent.mkdir(parents=True)
        path.write_text(self._row(1, "01") + self._row(2, "") + self._row(3, "00") + self._row(4, "99"), encoding="utf-8")
        country = country_model("DM", "DMO")
        admin1 = SubdivisionModel(name="One", iso_code=None, geonames_code="DM.01", geonames_id=10, type=None, aliases=[], admin_level=1, parent=None, country=country)

        cities, stats = load_cities.load_cities({"DM.01": admin1}, {"DM": country})

        assert [c.subdivisions for c in cities] == [[admin1], [], [], []]
        assert stats == {"ascii_names": 0, "unlinked_no_admin1": 1, "unlinked_admin1_00": 1, "unlinked_unknown_admin1": 1}

    def test_raises_on_changed_columns(self, repo):
        """should raise on a row whose field count isn't the file's documented columns"""
        load_cities = importlib.import_module("ingest.cities.scripts.load_cities")
        path = paths.Stage("cities").inputs / "cities500.txt"
        path.parent.mkdir(parents=True)
        path.write_text(self._row(1, "01").replace("\n", "\textra\n"), encoding="utf-8")

        with pytest.raises(ValueError):
            load_cities.load_cities({}, {"DM": country_model("DM", "DMO")})
