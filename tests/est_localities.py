from villager import localities, Locality
from utils import mangle


class TestGet:
    def test_id(self):
        for l in localities:
            locality = localities.get(l.villager_id)
            assert isinstance(locality, Locality)
            assert locality is not None
            assert l.name == locality.name

    def test_id_long_type(self):
        test = localities[0]
        locality = localities.get(f"way:{test.osm_id}")

        assert isinstance(locality, Locality)
        assert locality is not None
        assert test.name == locality.name

    def test_normalized(self):
        test = localities[0]
        locality = localities.get(f"   {test.villager_id.upper()}   ")
        assert isinstance(locality, Locality)
        assert locality is not None
        assert test.name == locality.name


class TestLookup:
    def test_lookup(self):
        for l in localities:
            results = localities.lookup(l.name)
            assert results
            assert isinstance(results, list)
            assert len(results) > 0
            assert l.name in [r.name for r in results]

    def test_is_normalized(self):
        test = localities[0]
        results = localities.lookup(f"   {test.name.upper()}   ")
        assert isinstance(results, list)
        assert results, "Expected at least one result"
        assert test.name in [r.name for r in results]
