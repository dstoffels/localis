from localis.registries import Registry
from utils import registry_param


@registry_param
class TestIteration:
    """ITERATION"""

    def test_len_matches_iteration(self, registry: Registry):
        """should count in len() exactly the records iteration yields"""
        assert len(registry) == sum(1 for _ in registry)
