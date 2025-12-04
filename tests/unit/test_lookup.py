from localis.registries import Registry
from localis.models import DTO
from utils import registry_param


@registry_param
class TestLookup:
    """LOOKUP"""

    def test_invalid(self, registry: Registry):
        """should return None with a bad lookup value"""

        invalid_value = "nonexistent_lookup_value_12345"
        result = registry.lookup(invalid_value)
        assert (
            result is None
        ), f"expected None, got {result} from lookup [{invalid_value}]"

    def test_valid(self, registry: Registry, select_random):
        """should return a DTO with a valid lookup value from each lookup field"""

        lookup_fields = registry._MODEL_CLS.LOOKUP_FIELDS

        subject: DTO = select_random(registry)

        for field in lookup_fields:
            lookup_value = getattr(subject, field)
            result = registry.lookup(lookup_value)
            assert (
                result is not None
            ), f"expected a result, got None for lookup field {field} with value {lookup_value}"
            assert isinstance(
                result, DTO
            ), f"expected a DTO, got {type(result)} for lookup field {field}"
            assert (
                getattr(result, field) == lookup_value
            ), f"expected [{field}: {lookup_value}], got [{getattr(result, field)}]"
