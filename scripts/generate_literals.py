from piecountry import countries, subdivisions
from pathlib import Path

dest = Path(__file__).parent.parent / "piecountry" / "literals.py"

alpha2_codes = sorted(set(c.alpha2 for c in countries))
alpha3_codes = sorted(set(c.alpha3 for c in countries))
codes = sorted([*alpha2_codes, *alpha3_codes])
names = sorted(set(c.name for c in countries))
numerics = sorted(set(c.numeric for c in countries))

with open(dest, "w", encoding="utf-8") as f:
    f.write("from typing import Literal\n\n")
    f.write(f"CountryCode = Literal[{', '.join(repr(code) for code in codes)}]\n")
    f.write(f"CountryName = Literal[{', '.join(repr(name) for name in names)}]\n")
    f.write(f"CountryNumeric = Literal[{', '.join(repr(num) for num in numerics)}]\n")
