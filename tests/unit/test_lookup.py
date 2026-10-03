from localis.registries import (
    Registry,
    MacroregionRegistry,
    CountryRegistry,
    SubdivisionRegistry,
    CityRegistry,
)
from localis.entities import Entity
from utils import registry_param

# Explicit per-registry callbacks over the runtime Entity's own shape, not derived from the
# ingestion-side Model: a historic country has no alpha2/alpha3/numeric lookup (those collide
# across historic entries), only its own historic.alpha_4 withdrawal code.
LOOKUP_VALUES_BY_REGISTRY = {
    MacroregionRegistry: lambda m: (m.code, m.name),
    CountryRegistry: lambda c: (
        (c.historic.alpha_4,) if c.historic else (c.alpha2, c.alpha3, c.numeric)
    ),
    SubdivisionRegistry: lambda s: (s.iso_code, s.geonames_code),
    CityRegistry: lambda c: (c.geonames_id,),
}


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
        """should resolve any randomly selected entity via each of its own valid lookup values"""

        get_values = LOOKUP_VALUES_BY_REGISTRY[type(registry)]

        subject: Entity = select_random(registry)
        values = [v for v in get_values(subject) if v]

        offset = 1
        while not values:
            subject = select_random(registry, offset)
            offset += 1
            values = [v for v in get_values(subject) if v]

        for value in values:
            result = registry.lookup(value)
            assert (
                result is not None
            ), f"expected a result, got None for lookup value [{value}]"
            assert isinstance(
                result, Entity
            ), f"expected an Entity, got {type(result)} for lookup value [{value}]"
            assert (
                result.id == subject.id
            ), f"expected id [{subject.id}], got [{result.id}] for lookup value [{value}]"
