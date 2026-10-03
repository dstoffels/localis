from localis.registries import Registry
from utils import registry_param

SAMPLE = 2000


def _resolve(view: object, field: str) -> object:
    value: object = view
    for attr in field.split("."):
        value = getattr(value, attr, None)
        if value is None:
            return None
    return value


@registry_param
def test_search_fields_resolve(registry: Registry):
    """every shipped search field resolves to a value on some entry, so none is silently dropped from scoring."""
    views = list(registry._cache.values())[:SAMPLE]
    for field in registry._search_index.SEARCH_FIELDS:
        assert any(_resolve(v, field) for v in views), f"search field '{field}' resolves to nothing on {type(registry).__name__}'s views"
