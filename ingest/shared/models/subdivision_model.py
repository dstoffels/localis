from dataclasses import dataclass
from .model import Model
from .country_model import CountryModel
from localis.utils.strings import normalize
import hashlib


@dataclass(slots=True)
class SubdivisionModel(Model):
    iso_code: str | None
    geonames_code: str | None
    geonames_id: int | None
    type: str | None
    aliases: list[str]
    admin_level: int
    parent: "SubdivisionModel | None"
    country: CountryModel
    hashid: int | None = None
    # ISO's parent for this subdivision, the key SubdivisionMap.refresh() links parent by; ingest-only, since the parent object it names may be merged away before then
    parent_iso_code: str | None = None

    UNSHIPPED_FIELDS = ("id", "hashid", "parent_iso_code")
    LOOKUP_FIELDS = ("iso_code", "geonames_code")
    FILTER_FIELDS = {
        "name": ("name", "aliases"),
        "type": ("type",),
        "country": (
            "country.name",
            "country.common_name",
            "country.alpha2",
            "country.alpha3",
            "country.numeric",
            "padded_country_numeric",
        ),
        "admin_level": ("admin_level",),
    }
    CANON_FIELDS = ("name", "aliases", "iso_suffix")
    SHORT_NAMES = True
    CONTEXT_FIELDS = ("parent.name", "country.name", "country.alpha2", "country.alpha3")

    @property
    def iso_suffix(self) -> str:
        return self.iso_code.split("-")[1] if self.iso_code else ""

    @property
    def padded_country_numeric(self) -> str | None:
        """The country's numeric code as ISO writes it, zero-padded to three digits ("076")."""
        return f"{self.country.numeric:03d}" if self.country.numeric is not None else None

    def row_values(self) -> dict[str, object]:
        data = Model.row_values(self)
        data["parent"] = self.parent.id if self.parent else None
        data["country"] = self.country.id
        data["aliases"] = self.join_cell(self.aliases)
        return data

    def set_hashid(self) -> None:
        """Sets hashid, the key SubdivisionMap holds a subdivision by before merging, when neither the ISO code nor the GeoNames id can key every subdivision; it never ships."""
        # the ISO code or the GeoNames code, whichever source the record was loaded from
        key = "|".join([self.country.alpha2, str(self.admin_level), normalize(self.name), self.iso_code or self.geonames_code or ""])
        self.hashid = int.from_bytes(hashlib.md5(key.encode()).digest()[:8], "big")
