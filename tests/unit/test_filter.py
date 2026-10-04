from typing import Any
import pytest
import localis
from localis.registries import (
    QueryableRegistry,
    CurrencyRegistry,
    CountryRegistry,
    SubdivisionRegistry,
    CityRegistry,
)
from localis.entities import Entity
from localis.utils.strings import normalize
from utils import queryable_registry_param


def _country_values(country_id: int) -> tuple:
    # the CountryBase embedded in subdivisions and cities lacks common_name and numeric, so read the full country
    c = localis.countries.get(country_id)
    assert c is not None
    return (c.name, c.common_name, c.alpha2, c.alpha3, c.numeric)


# Explicit per-registry callbacks returning every value a filter kwarg indexes for an entity, mirroring each model's FILTER_FIELDS.
FILTER_VALUES_BY_REGISTRY = {
    CurrencyRegistry: {},
    CountryRegistry: {
        "macroregion": lambda c: tuple(
            v for m in (*c.macroregions, *c.groupings) for v in (m.name, m.code)
        ),
        "currency": lambda c: tuple(v for m in c.currencies for v in (m.name, m.alpha3)),
    },
    SubdivisionRegistry: {
        "type": lambda s: (s.type,),
        "admin_level": lambda s: (s.admin_level,),
        "country": lambda s: _country_values(s.country.id),
    },
    CityRegistry: {
        "country": lambda c: _country_values(c.country.id)[:4],
        "subdivision": lambda c: tuple(
            v
            for s in c.subdivisions
            for v in (
                s.name,
                s.iso_code.split("-")[1] if s.iso_code else None,
                s.iso_code,
                s.geonames_code,
            )
        ),
    },
}


def _normalized(values: tuple) -> set[str]:
    return {normalize(str(v)) for v in values if v is not None and v != ""}


@queryable_registry_param
class TestFilter:
    """FILTER"""

    def test_none(self, registry: QueryableRegistry):
        """should return [] if no matches are found"""
        results = registry.filter(name="asjh238gjs")
        assert results == []

    def test_kwargs(self, registry: QueryableRegistry):
        """should raise a TypeError if given an invalid kwarg"""
        with pytest.raises(TypeError):
            registry.filter(pid="1234")

    def test_limit(self, registry: QueryableRegistry, select_random, include_historic):
        """should limit the number of results"""

        subject: Entity = select_random(registry)

        results = registry.filter(name=subject.name, limit=1)
        assert len(results) == 1

    def test_by_name(
        self, registry: QueryableRegistry, select_random, include_historic
    ):
        """should return a list of objects where the name field contains the name kwarg"""
        subject: Entity = select_random(registry)
        results: list[Entity] = registry.filter(name=subject.name)
        assert len(results) > 0, "should have at least 1 result"
        assert subject.id in [
            r.id for r in results
        ], f"subject ({subject.name}) should be in results: {results}"

    def test_and(self, registry: QueryableRegistry, select_random, include_historic):
        """should return only the results matching every kwarg when filtering by several"""
        subject: Entity = select_random(registry)
        by_name = {r.id for r in registry.filter(name=subject.name)}

        for kwarg, get_values in FILTER_VALUES_BY_REGISTRY[type(registry)].items():
            values = [v for v in get_values(subject) if v is not None and v != ""]
            if not values:
                continue

            filters: dict[str, Any] = {kwarg: values[0]}
            by_field = {r.id for r in registry.filter(**filters)}
            both = {r.id for r in registry.filter(name=subject.name, **filters)}
            assert (
                both == by_name & by_field
            ), f"expected the intersection of name=[{subject.name}] and {kwarg}=[{values[0]}], got: {both}"
            assert subject.id in both, f"subject ({subject.name}) should be in results for name and {kwarg}=[{values[0]}]"

    def test_missing(self, registry: QueryableRegistry, select_random, include_historic):
        """should return only entities with no value for a filter kwarg when filtered by MISSING, never one that has a value"""
        subject: Entity = select_random(registry)

        for kwarg, get_values in FILTER_VALUES_BY_REGISTRY[type(registry)].items():
            filters: dict[str, Any] = {kwarg: localis.MISSING}
            results = registry.filter(**filters)

            stray = [r.name for r in results if _normalized(get_values(r))]
            assert not stray, f"expected every result to have no {kwarg}, got: {stray[:10]}"
            if _normalized(get_values(subject)):
                assert subject.id not in {r.id for r in results}, f"subject ({subject.name}) has a {kwarg}, so shouldn't match {kwarg}=MISSING"

    def test_by_field(
        self, registry: QueryableRegistry, select_random, include_historic
    ):
        """should return a randomly selected entity when filtered by each of its values for each filter kwarg, and only results sharing that value"""

        for kwarg, get_values in FILTER_VALUES_BY_REGISTRY[type(registry)].items():
            subject: Entity = select_random(registry)
            values = [v for v in get_values(subject) if v is not None and v != ""]

            offset = 1
            while not values:
                subject = select_random(registry, offset)
                offset += 1
                values = [v for v in get_values(subject) if v is not None and v != ""]

            for value in values:
                filters: dict[str, Any] = {kwarg: value}
                results = registry.filter(**filters)
                assert subject.id in [
                    r.id for r in results
                ], f"subject ({subject.name}) should be in results for {kwarg}=[{value}]"

                stray = [
                    r.name
                    for r in results
                    if normalize(str(value)) not in _normalized(get_values(r))
                ]
                assert (
                    not stray
                ), f"expected every result to share {kwarg}=[{value}], got: {stray[:10]}"
