from pathlib import Path
from typing import Mapping, cast
from localis.entities import Language, LanguageBase, LanguageScope, LanguageType, LanguageScript
from localis.stores import LanguageStore
from .view import View, ViewMap
from .script_view import ScriptView


class LanguageView(View[Language, LanguageStore]):
    """Runtime view over LanguageStore, used by Registry._cache; resolves its scripts against the script view mapping."""

    __slots__ = ("_script_views",)

    def __init__(self, id: int, store: LanguageStore, script_views: Mapping[int, ScriptView]):
        super().__init__(id, store)
        self._script_views = script_views

    @property
    def name(self) -> str:
        return self._store.names[self._idx]

    @property
    def alpha3(self) -> str:
        return self._store.alpha3s[self._idx]

    @property
    def alpha2(self) -> str | None:
        v = self._store.alpha2s[self._idx]
        return v if v else None

    @property
    def bibliographic(self) -> str | None:
        v = self._store.bibliographics[self._idx]
        return v if v else None

    @property
    def scope(self) -> LanguageScope:
        return cast(LanguageScope, self._store.scopes[self._idx])

    @property
    def type(self) -> LanguageType:
        return cast(LanguageType, self._store.types[self._idx])

    @property
    def inverted_name(self) -> str | None:
        v = self._store.inverted_names[self._idx]
        return v if v else None

    @property
    def aliases(self) -> tuple[str, ...]:
        return self._store.aliases[self._idx]

    @property
    def scripts(self) -> list[LanguageScript]:
        idx = self._idx
        return [
            LanguageScript(id=view.id, name=view.name, alpha4=view.alpha4, secondary=secondary)
            for ids, secondary in ((self._store.script_ids[idx], False), (self._store.secondary_script_ids[idx], True))
            for view in (self._script_views[i] for i in ids)
        ]

    def to_base(self) -> LanguageBase:
        return LanguageBase(id=self.id, name=self.name, alpha3=self.alpha3, alpha2=self.alpha2)

    def to_entity(self) -> Language:
        return Language(
            id=self.id,
            name=self.name,
            alpha3=self.alpha3,
            alpha2=self.alpha2,
            bibliographic=self.bibliographic,
            scope=self.scope,
            type=self.type,
            inverted_name=self.inverted_name,
            aliases=list(self.aliases),
            scripts=self.scripts,
        )

    @classmethod
    def load(cls, filepath: Path, script_views: Mapping[int, ScriptView]) -> ViewMap["LanguageView"]:
        store = LanguageStore()
        with open(filepath, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                name, alpha3, alpha2, bibliographic, scope, type_, inverted_name, alias_s, scripts_s, secondary_s = line.rstrip("\r\n").split("\t")
                store.id_to_idx.append(idx)
                store.append(
                    name,
                    alpha3,
                    alpha2,
                    bibliographic,
                    scope,
                    type_,
                    inverted_name,
                    tuple(a for a in alias_s.split("|") if a),
                    tuple(int(i) for i in scripts_s.split("|") if i),
                    tuple(int(i) for i in secondary_s.split("|") if i),
                )
        return ViewMap(store, lambda id: cls(id, store, script_views))
