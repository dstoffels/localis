from ingest.utils import SUBDIVISIONS_RAW_PATH
from ingest.subdivisions.utils.strings import dedupe
from ingest.subdivisions import SubdivisionModel
import csv


def merge_ipregistry_aliases(iso_subs: dict[str, SubdivisionModel]) -> None:
    """Alias-only enrichment; iso-codes is the source of truth, Ipregistry's sourcing is unverifiable."""
    print("Merging Ipregistry alias data...")
    with open(
        SUBDIVISIONS_RAW_PATH / "ipregistry_subdivisions.csv", "r", encoding="utf-8"
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            iso_code = row["subdivision_code_iso3166-2"]
            local_variant = row["localVariant"]

            subdivision = iso_subs.get(iso_code)
            if not subdivision or not local_variant:
                continue

            if (
                local_variant != subdivision.name
                and local_variant not in subdivision.aliases
            ):
                subdivision.aliases.append(local_variant)

    for subdivision in iso_subs.values():
        subdivision.aliases = dedupe(subdivision.aliases)
