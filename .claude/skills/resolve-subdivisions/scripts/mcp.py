from utils import *
from mcp.server import MCPServer

mcp = MCPServer(name="resolve-subdivisions")


@mcp.tool(name="next")
def next(page: int = None) -> dict:
    for iso_code, entry in read_orphaned().items():
        if entry.get("skipped"):
            continue
        result = {"iso_code": iso_code, **entry}
        if page is not None:
            result["candidates"] = get_country_candidates_page(iso_code, page)
        return result
    return None


@mcp.tool(name="merge")
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


@mcp.tool(name="add")
def add(iso_code: str, names: list[str] = None) -> str:
    orphan = get_orphan(iso_code)

    write_resolution(iso_code, {"added": True, "names": names or []})
    pop_orphan(iso_code)

    line = f"ADD    {iso_code}  {orphan['name']!r}"
    if names:
        line += f"  +names={names}"
    log_decision(line)
    return line


@mcp.tool(name="skip")
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
    mcp.run()
