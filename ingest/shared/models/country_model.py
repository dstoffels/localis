from dataclasses import dataclass

from .model import Model
from localis.utils.strings import normalize


@dataclass(slots=True)
class CountryModel(Model):
    alpha2: str
    alpha3: str | None
    geonames_id: int | None
    official_name: str
    aliases: list[str]
    numeric: int | None
    flag: str | None
    historic: str | None

    LOOKUP_FIELDS = ("alpha2", "alpha3", "numeric")
    FILTER_FIELDS = {"name": ("name", "official_name", "aliases")}
    SEARCH_FIELDS = {
        "name": 1.0,
        "official_name": 1.0,
        "aliases": 1.0,
    }

    def extract_lookup_values(self):
        """Historic entries reuse alpha2/alpha3/numeric across different withdrawn countries (e.g. CS: Czechoslovakia vs. Serbia and Montenegro, both numeric 891), so only the unique alpha_4 withdrawal code is a safe lookup key for them."""
        if self.historic:
            # only the unique alpha_4 withdrawal code is used for historic entries
            yield normalize(self.historic.split("|", 1)[0])
            return
        yield from Model.extract_lookup_values(self)

    def to_row(self) -> tuple[str | int | None]:
        data = self.to_dict()
        data["aliases"] = "|".join(self.aliases)
        data.pop("id")
        return tuple(data.values())
