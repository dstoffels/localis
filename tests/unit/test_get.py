from localis.registries import Registry
from localis.models import DTO
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
        """should return a DTO with a valid ID"""

        # all datasets have an entry with ID 10
        valid_id = 10
        result = registry.get(valid_id)
        assert result is not None, "expected a result, got None"
        assert isinstance(result, DTO), f"expected a DTO, got {type(result)}"
        assert result.id == valid_id, f"expected ID {valid_id}, got {result.id}"
