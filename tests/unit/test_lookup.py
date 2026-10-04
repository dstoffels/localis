import localis
from localis.registries import (
    Registry,
    MacroregionRegistry,
    CurrencyRegistry,
    CountryRegistry,
    SubdivisionRegistry,
    CityRegistry,
)
from localis.entities import Entity
from utils import registry_param

# each entity's own lookup values, written out rather than derived from the ingest models; a historic country looks up by its alpha_4 only, since its alpha2/alpha3/numeric collide
LOOKUP_VALUES_BY_REGISTRY = {
    MacroregionRegistry: lambda m: (m.code, m.name),
    CurrencyRegistry: lambda c: (c.alpha3, c.numeric),
    CountryRegistry: lambda c: (
        (c.historic.alpha_4,) if c.historic else (c.alpha2, c.alpha3, c.numeric)
    ),
    SubdivisionRegistry: lambda s: (s.iso_code, s.geonames_code),
    CityRegistry: lambda c: (c.geonames_id,),
}

# each entity's nested base entities, with the registry their key resolves in
NESTED_BY_REGISTRY = {
    MacroregionRegistry: lambda m: [(m.parent, localis.macroregions)],
    CurrencyRegistry: lambda c: [],
    CountryRegistry: lambda c: [
        *((m, localis.macroregions) for m in (*c.macroregions, *c.groupings)),
        *((m, localis.currencies) for m in c.currencies),
    ],
    SubdivisionRegistry: lambda s: [(s.parent, localis.subdivisions), (s.country, localis.countries)],
    CityRegistry: lambda c: [*((s, localis.subdivisions) for s in c.subdivisions), (c.country, localis.countries)],
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

    def test_key(self, registry: Registry, select_random):
        """should resolve a randomly selected entity, and every entity nested in it, via its key"""
        subject: Entity = select_random(registry)
        result = registry.lookup(subject.key)
        assert result is not None and result.id == subject.id, f"expected id [{subject.id}] for key [{subject.key}], got {result}"

        for base, base_registry in NESTED_BY_REGISTRY[type(registry)](subject):
            if base is None:
                continue
            resolved = base_registry.lookup(base.key)
            assert resolved is not None and resolved.id == base.id, f"expected nested id [{base.id}] for key [{base.key}], got {resolved}"

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
