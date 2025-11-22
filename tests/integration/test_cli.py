import pytest
import localis
from localis.data import db


@pytest.mark.slow
class TestLoadCities:
    """LOADING"""

    def test_unloadcities(self):
        """should remove the cities dataset and throw exception when cities is accessed to confirm."""
        db.close()

        localis.cities.unload()

        assert (
            localis.cities._loaded == False
        ), "expected cities loaded flag to be false"

        try:
            localis.cities.get(id=1)
        except RuntimeError as e:
            assert e, "expected a runtime error"
            return
        assert False, "expected accessing the cities registry to raise a runtime error."

    def test_loadcities(self):
        """should download and load cities dataset into db (!!! SLOW: ~10s !!!)."""

        localis.cities.load(confirmed=True)

        assert localis.cities._loaded, "expected cities loaded flag to be true"

        try:
            localis.cities.get(id=1)
            return
        except RuntimeError:
            assert False, "expected accessing cities to run without exception."
