from pathlib import Path
from localis.entities import Script, ScriptBase
from localis.stores import ScriptStore
from .view import View, ViewMap


class ScriptView(View[Script, ScriptStore]):
    """Runtime view over ScriptStore, used by Registry._cache."""

    __slots__ = ()

    @property
    def name(self) -> str:
        return self._store.names[self._idx]

    @property
    def alpha4(self) -> str:
        return self._store.alpha4s[self._idx]

    @property
    def numeric(self) -> int | None:
        v = self._store.numerics[self._idx]
        return v if v != -1 else None

    @property
    def aliases(self) -> tuple[str, ...]:
        return self._store.aliases[self._idx]

    def to_base(self) -> ScriptBase:
        return ScriptBase(id=self.id, name=self.name, alpha4=self.alpha4)

    def to_entity(self) -> Script:
        return Script(id=self.id, name=self.name, alpha4=self.alpha4, numeric=self.numeric, aliases=self.aliases)

    @classmethod
    def load(cls, filepath: Path) -> ViewMap["ScriptView"]:
        store = ScriptStore()
        with open(filepath, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                name, alpha4, numeric_s, alias_s = line.rstrip("\r\n").split("\t")
                store.id_to_idx.append(idx)
                store.append(name, alpha4, int(numeric_s) if numeric_s else None, tuple(a for a in alias_s.split("|") if a))
        return ViewMap(store, lambda id: cls(id, store))
