import localis
import argparse


def loadcities(args):
    """Load the cities dataset"""
    localis.cities.load(confirmed=args.yes, custom_dir=args.path)


def unloadcities(args):
    localis.cities.unload()


def main():
    parser = argparse.ArgumentParser(prog="localis", description="localis CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # LOADCITIES
    loadcities_parser = subparsers.add_parser(
        "loadcities", help="Load the cities data into localis"
    )
    loadcities_parser.add_argument("-y", "--yes", action="store_true")
    loadcities_parser.add_argument("-p", "--path", default=None)

    loadcities_parser.set_defaults(func=loadcities)

    # UNLOADCITIES
    unloadcities_parser = subparsers.add_parser(
        "unloadcities", help="Remove the cities dataset from localis"
    )
    unloadcities_parser.set_defaults(func=unloadcities)

    args = parser.parse_args()

    args.func(args)


if __name__ == "__main__":
    main()
