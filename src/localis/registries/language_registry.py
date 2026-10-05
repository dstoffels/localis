from typing import Mapping, cast
from localis.entities import Language
from localis.indexes import Missing
from localis.views import LanguageView, ScriptView
from localis.registries import QueryableRegistry, ScriptRegistry


class LanguageRegistry(QueryableRegistry[Language]):
    REGISTRY_NAME = "languages"
    NAME_FIELDS = ("name", "inverted_name", "aliases")

    def __init__(self, scripts: ScriptRegistry):
        self._scripts = scripts
        super().__init__()

    def _build_cache(self) -> Mapping[int, LanguageView]:
        script_views = cast(Mapping[int, ScriptView], self._scripts._cache)
        return LanguageView.load(self._data_filepath, script_views)

    def lookup(self, identifier: str | int) -> Language | None:
        """Get a language by its ISO 639-3 alpha3, ISO 639-1 alpha2 or ISO 639-2/B bibliographic code; use .get() for the localis id."""
        return super().lookup(identifier)

    def filter(
        self,
        *,
        name: str | None = None,
        limit: int | None = None,
        scope: str | None = None,
        type: str | None = None,
        script: str | Missing | None = None,
    ) -> list[Language]:
        """Filter languages by name (name, inverted_name or alias), scope, type or a script (by alpha4, name or alias, primary or secondary); script=MISSING matches languages with none."""
        return self._filter(limit, name=name, scope=scope, type=type, script=script)

    def search(self, query: str, limit: int = 10) -> list[tuple[Language, float]]:
        """Search languages by name, inverted_name or alias."""
        return super().search(query, limit)


# --------- Singleton --------- #
from localis.registries.script_registry import scripts

languages = LanguageRegistry(scripts=scripts)
