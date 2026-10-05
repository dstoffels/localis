from importlib.metadata import version
import localis


class TestPublicApi:
    """PUBLIC API"""

    def test_all_resolves(self):
        """should define every name __all__ exports"""
        missing = [name for name in localis.__all__ if not hasattr(localis, name)]

        assert not missing

    def test_all_unique(self):
        """should list each exported name once"""
        assert len(localis.__all__) == len(set(localis.__all__))

    def test_version(self):
        """should report the installed package version"""
        assert localis.__version__ == version("localis")
