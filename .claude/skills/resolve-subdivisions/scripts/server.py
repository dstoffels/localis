from utils import *
from mcp.server import MCPServer

mcp = MCPServer(name="resolve-subdivisions")

MAX_CANDIDATES = 1000
processed_candidates = 0


@mcp.tool(name="next")
def next(return_all: bool = False) -> dict:
    """Returns the next orphaned subdivision, optionally with a page of candidates.

    Args:
        return_all (bool): Whether to return all candidates or just the top tier.
    """
    global processed_candidates
    if processed_candidates >= MAX_CANDIDATES:
        return "MAX CANDIDATES REACHED: Tell the user to have you call the reset tool, then /clear to clear context. The next tool will not return candidates until the count is reset."

    for iso_code, entry in read_orphaned().items():
        if entry.get("skipped"):
            continue
        result = {"iso_code": iso_code, **entry}
        candidates = get_candidates(iso_code, return_all)
        result["candidates"] = candidates
        processed_candidates += len(candidates)
        return result
    return None


@mcp.tool(name="merge")
def merge(iso_code: str, geo_sub_hashid: str, names: list[str] = []) -> str:
    """Merges an orphaned subdivision into an existing country candidate.

    Args:
        iso_code (str): The ISO code of the orphaned subdivision.
        geo_sub_hashid (int): The hashid of the geonames subdivision to merge into.
        names (list[str], optional): Additional names for the subdivision.
    """
    orphan = get_orphan(iso_code)

    if orphan is None:
        return "ERROR: INVALID ISO CODE FOR ORPHAN"

    candidate = get_geonames_submap().get(int(geo_sub_hashid))
    if candidate is None:
        return "ERROR: INVALID HASHID FOR GEONAMES CANDIDATE"

    write_resolution(iso_code, {"hashid": geo_sub_hashid, "names": names})
    pop_orphan(iso_code)

    line = (
        f"MERGE  {iso_code}  {orphan['name']!r} -> {geo_sub_hashid} {candidate.name!r}"
    )
    if names:
        line += f"  +names={names}"
    log_decision(line)
    return "SUCCESS"


@mcp.tool(name="add")
def add(iso_code: str, names: list[str] = []) -> str:
    """Adds an orphaned subdivision as a new entry.

    Args:
        iso_code (str): The ISO code of the orphaned subdivision.
        names (list[str], optional): Additional names for the subdivision.
    """

    orphan = get_orphan(iso_code)

    if orphan is None:
        return "ERROR: INVALID ISO CODE FOR ORPHAN"

    write_resolution(iso_code, {"added": True, "names": names})
    pop_orphan(iso_code)

    line = f"ADD    {iso_code}  {orphan['name']!r}"
    if names:
        line += f"  +names={names}"
    log_decision(line)
    return "SUCCESS"


@mcp.tool(name="reset")
def reset() -> str:
    """Resets the processed candidates count."""
    global processed_candidates
    processed_candidates = 0
    return "SUCCESS"


# @mcp.tool(name="skip")
# def skip(iso_code: str, reason: str) -> str:
#     """Leaves an orphaned subdivision unresolved for a human, annotated with why. Does not touch
#     resolution_map.json -- if it's still in orphaned_subdivisions.json when the interactive
#     wizard runs, it'll show up there, same as any other unresolved entry. Returns (and logs)
#     a human-readable line."""
#     orphan = get_orphan(iso_code)

#     if orphan is None:
#         return "ERROR: INVALID ISO CODE FOR ORPHAN"

#     mark_skipped(iso_code, reason)

#     line = f"SKIP   {iso_code}  {orphan['name']!r} - {reason}"
#     log_decision(line)
#     return "SUCCESS"


if __name__ == "__main__":
    mcp.run(transport="stdio")
