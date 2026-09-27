from utils import *
from mcp.server import MCPServer

mcp = MCPServer(name="resolve-subdivisions")

MAX_CANDIDATES = 1000
processed_candidates = 0
batch_num = 0


@mcp.tool(name="next")
def next() -> dict | str | None:
    """Returns the next orphaned subdivision and its candidates. Repeated calls paginate through the candidates until all candidates have been processed.

    Candidates are flat formatted: { hashid: "name1, name2  [admin_level]", ... }
    """
    global processed_candidates, batch_num

    # We cannot reset the session while there are still unprocessed candidates for an orphan.
    # The first batch is 10-100 candidates, subsequent batches are fixed at 200, so processed_candidates will never be > MAX_CANDIDATES after the first batch (batch_num=0).
    # processed_candidates can only reach MAX_CANDIDATES after a minimum of 6 repeated next calls for orphans with over 1000 candidates.
    # An orphan is finished processing after calling merge or add, and batch_num is reset to 0. After which, if more than 1000 candidates have been processed, the next orphan will trigger the MAX_CANDIDATES check, forcing the user to reset the session context.

    # Reset session context and counters to reduce agent context drift.
    if processed_candidates >= MAX_CANDIDATES and batch_num == 0:
        processed_candidates = 0
        return "MAX CANDIDATES REACHED: Tell the user to call /clear to reset session context and then cease all further processing in this session."

    orphan = get_next_orphan()
    if orphan is None:
        return None

    candidates = get_candidates(orphan["iso_code"], batch_num)

    if candidates is None:
        batch_num = 0
        return "END OF CANDIDATES FOR THIS ORPHAN"

    orphan["candidates"] = candidates

    batch_num += 1
    processed_candidates += len(orphan["candidates"])
    return orphan


@mcp.tool(name="merge")
def merge(iso_code: str, geo_sub_hashid: str, alt_names: list[str] = []) -> str:
    """Merges an orphaned subdivision into an existing country candidate.

    Args:
        iso_code (str): The ISO code of the orphaned subdivision.
        geo_sub_hashid (int): The hashid of the geonames subdivision to merge into.
        alt_names (list[str], optional): Additional names for the subdivision.
    """
    orphan = get_orphan(iso_code)

    if orphan is None:
        return "ERROR: INVALID ISO CODE FOR ORPHAN"
    hashid = int(geo_sub_hashid)

    if not is_valid_candidate(iso_code, hashid):
        return "ERROR: INVALID CANDIDATE FOR ISO CODE"

    candidate = get_geonames_submap().get(hashid)

    write_resolution(iso_code, {"hashid": hashid, "names": alt_names})
    pop_orphan(iso_code)

    line = (
        f"MERGE  {iso_code}  {orphan['name']!r} -> {geo_sub_hashid} {candidate.name!r}"
    )
    if alt_names:
        line += f"  +names={alt_names}"
    log_decision(line)

    global batch_num
    batch_num = 0

    return "SUCCESS"


@mcp.tool(name="add")
def add(iso_code: str, alt_names: list[str] = []) -> str:
    """Adds an orphaned subdivision as a new entry.

    Args:
        iso_code (str): The ISO code of the orphaned subdivision.
        alt_names (list[str], optional): Additional names for the subdivision.
    """

    orphan = get_orphan(iso_code)

    if orphan is None:
        return "ERROR: INVALID ISO CODE FOR ORPHAN"

    write_resolution(iso_code, {"added": True, "names": alt_names})
    pop_orphan(iso_code)

    line = f"ADD    {iso_code}  {orphan['name']!r}"
    if alt_names:
        line += f"  +names={alt_names}"
    log_decision(line)

    global batch_num
    batch_num = 0

    return "SUCCESS"


@mcp.tool(name="review")
def review() -> str:
    """Dumps the next orphan and all its candidates to review_output.json for the user to manually review and decide on the resolution. Prompt the user to call add or merge (with the selected hashid)"""

    orphan = get_next_orphan()

    if orphan is None:
        return "NO ORPHANS TO REVIEW"

    orphan["top_candidates"] = get_candidates(
        orphan["iso_code"], batch_num=batch_num, return_all=True
    )

    write_orphan_for_review(orphan)

    return "SUCCESS"


if __name__ == "__main__":
    mcp.run(transport="stdio")
