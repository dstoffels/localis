from data.utils import download, GEONAMES_DUMP_URL, SUBDIVISIONS_RAW_PATH

IPREGISTRY_SUBDIVISIONS_URL = (
    "https://raw.githubusercontent.com/ipregistry/iso3166/main/subdivisions.csv"
)


def fetch_subdivisions_sources() -> None:
    download(
        f"{GEONAMES_DUMP_URL}/admin1CodesASCII.txt",
        SUBDIVISIONS_RAW_PATH / "admin1CodesASCII.txt",
    )
    download(
        f"{GEONAMES_DUMP_URL}/admin2Codes.txt", SUBDIVISIONS_RAW_PATH / "admin2.txt"
    )
    download(IPREGISTRY_SUBDIVISIONS_URL, SUBDIVISIONS_RAW_PATH / "iso-3166-2.csv")
