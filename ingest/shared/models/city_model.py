from dataclasses import dataclass
from .model import Model
from .country_model import CountryModel
from .subdivision_model import SubdivisionModel


@dataclass(slots=True)
class CityModel(Model):
    geonames_id: int
    subdivisions: list[SubdivisionModel]
    country: CountryModel | None
    population: int
    lat: float
    lng: float

    LOOKUP_FIELDS = ("geonames_id",)
    FILTER_FIELDS = {
        "name": ("name",),
        "country": (
            "country.name",
            "country.common_name",
            "country.alpha2",
            "country.alpha3",
        ),
        "subdivision": (
            "subdivision_names",
            "subdivision_iso_suffixes",
            "subdivision_iso_codes",
            "subdivision_geonames_codes",
        ),
    }
    CANON_FIELDS = ("name",)
    SHORT_NAMES = True
    CONTEXT_FIELDS = ("admin1.name", "admin1.iso_suffix", "country.name", "country.alpha2", "country.alpha3")

    @property
    def admin1(self) -> SubdivisionModel | None:
        """The city's admin_level=1 subdivision (state/province), the only level in CONTEXT_FIELDS; the rest of the chain is too noisy/bloating for the trigram index."""
        return next((s for s in self.subdivisions if s.admin_level == 1), None)

    @property
    def subdivision_names(self) -> list[str]:
        return [s.name for s in self.subdivisions]

    @property
    def subdivision_iso_suffixes(self) -> list[str]:
        return [s.iso_suffix for s in self.subdivisions if s.iso_suffix]

    @property
    def subdivision_iso_codes(self) -> list[str]:
        return [s.iso_code for s in self.subdivisions if s.iso_code]

    @property
    def subdivision_geonames_codes(self) -> list[str]:
        return [s.geonames_code for s in self.subdivisions if s.geonames_code]

    def row_values(self) -> dict[str, object]:
        data = Model.row_values(self)
        data["subdivisions"] = "|".join(str(s.id) for s in self.subdivisions)
        data["country"] = self.country.id if self.country else None
        return data
