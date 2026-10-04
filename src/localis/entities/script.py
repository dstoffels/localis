from dataclasses import dataclass
from .entity import Entity


@dataclass(slots=True)
class ScriptBase(Entity):
    alpha4: str

    @property
    def key(self) -> str:
        """The stable reference to store instead of id, resolved by scripts.lookup(): the ISO 15924 alpha4."""
        return self.alpha4


@dataclass(slots=True)
class Script(ScriptBase):
    numeric: int | None
    aliases: tuple[str, ...]


@dataclass(slots=True)
class LanguageScript(ScriptBase):
    # CLDR's rule: the language or the script isn't modern
    secondary: bool
