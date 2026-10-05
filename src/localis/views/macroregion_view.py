import sys
from pathlib import Path
from typing import Mapping, cast
from localis.entities import Macroregion, MacroregionBase, MacroregionType
from localis.stores import MacroregionStore
from .view import View, ViewMap


class MacroregionView(View[Macroregion, MacroregionStore]):
    """Runtime view over MacroregionStore, used by Registry._cache; resolves its parent against its own view mapping."""

    __slots__ = ("_views",)

    def __init__(self, id: int, store: MacroregionStore, views: Mapping[int, "MacroregionView"]):
        super().__init__(id, store)
        self._views = views

    @property
    def name(self) -> str:
        return self._store.names[self._idx]

    @property
    def code(self) -> str:
        return self._store.codes[self._idx]

    @property
    def type(self) -> MacroregionType:
        return cast(MacroregionType, self._store.types[self._idx])

    @property
    def parent(self) -> "MacroregionView | None":
        pid = self._store.parent_ids[self._idx]
        return self._views.get(pid) if pid != -1 else None

    def to_base(self) -> MacroregionBase:
        return MacroregionBase(id=self.id, name=self.name, code=self.code, type=self.type)

    def to_entity(self) -> Macroregion:
        parent = self.parent
        return Macroregion(
            id=self.id,
            name=self.name,
            code=self.code,
            type=self.type,
            parent=parent.to_base() if parent else None,
        )

    @classmethod
    def load(cls, filepath: Path) -> ViewMap["MacroregionView"]:
        store = MacroregionStore()
        with open(filepath, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                name, code, type_, parent_s = line.rstrip("\r\n").split("\t")
                store.id_to_idx.append(idx)
                # interned, since three types repeat on every row
                store.append(name, code, sys.intern(type_), int(parent_s) if parent_s else None)
        # a macroregion's parent resolves against this same mapping
        views: ViewMap[MacroregionView] = ViewMap(store, lambda id: cls(id, store, views))
        return views
