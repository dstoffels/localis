"""Checks an installed localis wheel before it's published: its version, the files it must ship, and a round trip through every registry."""

import os
from importlib import metadata, resources
import localis

version = os.environ["VERSION"]
assert localis.__version__ == version, f"__version__ is {localis.__version__}, expected {version}"

package = resources.files("localis")
for path in ("py.typed", "data/NOTICE"):
    assert package.joinpath(path).is_file(), f"{path} is missing from the wheel"

licenses = {f.name for f in metadata.files("localis") or [] if "licenses" in f.parts}
for name in ("LICENSE", "LGPL-2.1-or-later.txt", "CC-BY-4.0.txt", "Unicode-3.0.txt", "CC0-1.0.txt"):
    assert name in licenses, f"{name} is missing from the wheel's licenses"

for name in localis.__all__:
    getattr(localis, name)

for registry in (localis.macroregions, localis.currencies, localis.scripts, localis.languages, localis.countries, localis.subdivisions, localis.cities):
    label = type(registry).__name__
    first = next(iter(registry), None)
    assert first is not None and len(registry) > 0, f"{label} has no records"
    assert registry.get(first.id) == first, f"{label}.get() doesn't return its first record"
    found = registry.lookup(first.key)
    assert found is not None and found.id == first.id, f"{label}.lookup() doesn't resolve its first record's key"
    if isinstance(registry, localis.QueryableRegistry):
        assert first.id in {r.id for r in registry.filter(name=first.name)}, f"{label}.filter() doesn't find its first record by name"
        assert registry.search(first.name), f"{label}.search() finds nothing for its first record's name"

print(f"localis {version} wheel checks out")
