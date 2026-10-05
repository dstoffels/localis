from .entity import Entity, entity


@entity
class ScriptBase(Entity):
    """A script as other records nest it."""

    alpha4: str

    @property
    def key(self) -> str:
        """The stable reference to store instead of id, resolved by scripts.lookup(): the ISO 15924 alpha4."""
        return self.alpha4


@entity
class Script(ScriptBase):
    """An ISO 15924 script code."""

    numeric: int | None
    aliases: list[str]


@entity
class LanguageScript(ScriptBase):
    """A script a language is written in, per CLDR."""

    # CLDR's rule: the language or the script isn't modern
    secondary: bool
