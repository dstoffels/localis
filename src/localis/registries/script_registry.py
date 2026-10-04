from typing import Mapping
from localis.entities import Script
from localis.views import ScriptView
from localis.registries import QueryableRegistry


class ScriptRegistry(QueryableRegistry[Script]):
    REGISTRY_NAME = "scripts"
    NAME_FIELDS = ("name", "aliases")

    def build_cache(self) -> Mapping[int, ScriptView]:
        return ScriptView.load(self._data_filepath)

    def lookup(self, identifier: str | int) -> Script | None:
        """Get a script by its ISO 15924 alpha4 or numeric code (an int); use .get() for the localis id."""
        return super().lookup(identifier)

    def filter(self, *, name: str | None = None, limit: int | None = None, **kwargs) -> list[Script]:
        """Filter scripts by name or alias."""
        return super().filter(name=name, limit=limit, **kwargs)

    def search(self, query: str, limit: int = 10) -> list[tuple[Script, float]]:
        """Search scripts by name or alias."""
        return super().search(query, limit)


# --------- Singleton --------- #
scripts = ScriptRegistry()
