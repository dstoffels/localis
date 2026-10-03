from typing import Mapping
from localis.entities import Macroregion
from localis.views import MacroregionView
from localis.registries import Registry


class MacroregionRegistry(Registry[Macroregion]):
    REGISTRY_NAME = "macroregions"

    def build_cache(self) -> Mapping[int, MacroregionView]:
        return MacroregionView.load(self._data_filepath)

    def lookup(self, identifier: str | int) -> Macroregion | None:
        """Get a macroregion by its code or name; M49 codes are zero-padded strings ("009"), so an int never matches. Use .get() for the localis id."""
        return super().lookup(identifier)


# --------- Singleton --------- #
macroregions = MacroregionRegistry()
