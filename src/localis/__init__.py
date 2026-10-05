from importlib.metadata import version

# core types and api singletons
from .entities import (
    Entity,
    Macroregion,
    MacroregionBase,
    MacroregionType,
    Currency,
    CurrencyBase,
    Script,
    ScriptBase,
    LanguageScript,
    Language,
    LanguageBase,
    CountryLanguage,
    LanguageScope,
    LanguageType,
    LanguageStatus,
    Country,
    CountryBase,
    HistoricInfo,
    Subdivision,
    SubdivisionBase,
    City,
)
from .registries import (
    Registry,
    QueryableRegistry,
    MacroregionRegistry,
    CurrencyRegistry,
    ScriptRegistry,
    LanguageRegistry,
    CountryRegistry,
    SubdivisionRegistry,
    CityRegistry,
)
from .registries.macroregion_registry import macroregions
from .registries.currency_registry import currencies
from .registries.script_registry import scripts
from .registries.language_registry import languages
from .registries.country_registry import countries
from .registries.subdivision_registry import subdivisions
from .registries.city_registry import cities
from .indexes import MISSING, Missing

__version__ = version("localis")

# the public surface; type checkers treat any import not listed here as private to the package
__all__ = [
    "__version__",
    "Entity",
    "Macroregion",
    "MacroregionBase",
    "MacroregionType",
    "Currency",
    "CurrencyBase",
    "Script",
    "ScriptBase",
    "LanguageScript",
    "Language",
    "LanguageBase",
    "CountryLanguage",
    "LanguageScope",
    "LanguageType",
    "LanguageStatus",
    "Country",
    "CountryBase",
    "HistoricInfo",
    "Subdivision",
    "SubdivisionBase",
    "City",
    "Registry",
    "QueryableRegistry",
    "MacroregionRegistry",
    "CurrencyRegistry",
    "ScriptRegistry",
    "LanguageRegistry",
    "CountryRegistry",
    "SubdivisionRegistry",
    "CityRegistry",
    "macroregions",
    "currencies",
    "scripts",
    "languages",
    "countries",
    "subdivisions",
    "cities",
    "MISSING",
    "Missing",
]
