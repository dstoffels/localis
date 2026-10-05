from dataclasses import fields
from localis.registries import Registry
from localis.entities import Entity
from utils import registry_param
import pytest


@registry_param
class TestGet:
    """GET"""

    @pytest.mark.parametrize("bad_id", [-9999, "invalid_id", None, True, 3.0])
    def test_invalid(self, bad_id, registry: Registry):
        """should return None with a bad ID"""

        result = registry.get(bad_id)
        assert result is None, f"expected None, got {result} from ID {bad_id}"

    def test_valid(self, registry: Registry, select_random):
        """should return an Entity with a valid ID"""

        subject: Entity = select_random(registry)
        result = registry.get(subject.id)
        assert result is not None, "expected a result, got None"
        assert isinstance(result, Entity), f"expected an Entity, got {type(result)}"
        assert result.id == subject.id, f"expected ID {subject.id}, got {result.id}"

    def test_hashable(self, registry: Registry, select_random):
        """should return results that hash by record, so the same record twice dedupes in a set"""

        subject: Entity = select_random(registry)
        offset = 1
        other: Entity = select_random(registry, offset)
        while other.id == subject.id:
            offset += 1
            other = select_random(registry, offset)

        first, again = registry.get(subject.id), registry.get(subject.id)
        assert first is not None and again is not None
        assert first == again and hash(first) == hash(again)
        assert len({first, again, other}) == 2

    def test_results_are_copies(self, registry: Registry, select_random):
        """should build every result fresh, so changing one, its lists and nested records included, leaves the loaded data as it was"""

        subject: Entity = select_random(registry)
        before = registry.get(subject.id)
        result = registry.get(subject.id)
        assert before is not None and result is not None

        for field in fields(result):
            value = getattr(result, field.name)
            if isinstance(value, Entity):
                value.name = "changed"
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, Entity):
                        item.name = "changed"
                value.clear()
        result.name = "changed"

        assert registry.get(subject.id) == before
