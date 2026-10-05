from localis.registries import Registry
from localis.entities import Entity
from utils import registry_param
import pytest


@registry_param
class TestGet:
    """GET"""

    @pytest.mark.parametrize("bad_id", [-9999, "invalid_id", None])
    def test_invalid(self, bad_id, registry: Registry):
        """should return None with a bad ID"""

        result = registry.get(bad_id)
        assert result is None, f"expected None, got {result} from ID {bad_id}"

    def test_valid(self, registry: Registry):
        """should return an Entity with a valid ID"""

        # all datasets have an entry with ID 10
        valid_id = 10
        result = registry.get(valid_id)
        assert result is not None, "expected a result, got None"
        assert isinstance(result, Entity), f"expected an Entity, got {type(result)}"
        assert result.id == valid_id, f"expected ID {valid_id}, got {result.id}"

    def test_hashable(self, registry: Registry):
        """should return results that hash by record, so the same record twice dedupes in a set"""

        first, again, other = registry.get(10), registry.get(10), registry.get(11)
        assert first is not None and again is not None and other is not None
        assert first == again and hash(first) == hash(again)
        assert len({first, again, other}) == 2

    def test_results_are_copies(self, registry: Registry):
        """should build every result fresh, so changing one leaves the loaded data and later results as they were"""

        result = registry.get(10)
        assert result is not None
        for name in ("aliases", "subdivisions", "scripts", "languages", "currencies", "macroregions"):
            value = getattr(result, name, None)
            if isinstance(value, list):
                value.clear()
        result.name = "changed"
        assert registry.get(10) == registry.get(10) != result
