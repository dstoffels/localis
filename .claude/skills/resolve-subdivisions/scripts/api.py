from utils import (
    write_resolution,
    read_orphaned,
    get_orphan,
    get_all_country_candidates,
    get_country_candidates_page,
    pop_orphan,
    mark_skipped,
    log_decision,
)


def next(page: int = None) -> dict:
    for iso_code, entry in read_orphaned().items():
        if entry.get("skipped"):
            continue
        result = {"iso_code": iso_code, **entry}
        if page is not None:
            result["candidates"] = get_country_candidates_page(iso_code, page)
        return result
    return None


def merge(iso_code: str, geo_sub: int, names: list[str] = None) -> str:
    orphan = get_orphan(iso_code)
    candidate = None
    for c in get_all_country_candidates(iso_code):
        if c["hashid"] == geo_sub:
            candidate = c
            break
    if candidate is None:
        raise ValueError(f"{geo_sub} is not a candidate hashid for {iso_code}")

    write_resolution(iso_code, {"hashid": geo_sub, "names": names or []})
    pop_orphan(iso_code)

    line = f"MERGE  {iso_code}  {orphan['name']!r} -> {geo_sub} {candidate['name']!r}"
    if names:
        line += f"  +names={names}"
    log_decision(line)
    return line


def add(iso_code: str, names: list[str] = None) -> str:
    orphan = get_orphan(iso_code)

    write_resolution(iso_code, {"added": True, "names": names or []})
    pop_orphan(iso_code)

    line = f"ADD    {iso_code}  {orphan['name']!r}"
    if names:
        line += f"  +names={names}"
    log_decision(line)
    return line


def skip(iso_code: str, reason: str) -> str:
    """Leaves iso_code unresolved for a human, annotated with why. Does not touch
    resolution_map.json -- if it's still in orphaned_subdivisions.json when the interactive
    wizard runs, it'll show up there, same as any other unresolved entry. Returns (and logs)
    a human-readable line."""
    orphan = get_orphan(iso_code)
    mark_skipped(iso_code, reason)

    line = f"SKIP   {iso_code}  {orphan['name']!r} - {reason}"
    log_decision(line)
    return line


if __name__ == "__main__":
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(
        description="CLI for resolving orphaned subdivisions."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    next_parser = subparsers.add_parser(
        "next",
        help="Print the current undecided orphan as JSON, or null if none remain. "
        "With <page>, also include that page of its country's candidates.",
    )
    next_parser.add_argument("page", type=int, nargs="?", default=None)

    merge_parser = subparsers.add_parser(
        "merge", help="Record iso_code as matching a candidate hashid."
    )
    merge_parser.add_argument("iso_code")
    merge_parser.add_argument("hashid", type=int)
    merge_parser.add_argument("--names", nargs="*", default=[])

    add_parser = subparsers.add_parser(
        "add", help="Record iso_code as a standalone addition."
    )
    add_parser.add_argument("iso_code")
    add_parser.add_argument("--names", nargs="*", default=[])

    skip_parser = subparsers.add_parser(
        "skip", help="Leave iso_code unresolved for a human, with a reason."
    )
    skip_parser.add_argument("iso_code")
    skip_parser.add_argument("reason")

    args = parser.parse_args()

    try:
        if args.command == "next":
            print(json.dumps(next(args.page)))
        elif args.command == "merge":
            print(merge(args.iso_code, args.hashid, args.names))
        elif args.command == "add":
            print(add(args.iso_code, args.names))
        elif args.command == "skip":
            print(skip(args.iso_code, args.reason))
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
