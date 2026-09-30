from utils import *
from mcp.server import MCPServer

mcp = MCPServer(name="resolve-subdivisions")

MAX_CANDIDATES = 1000
processed_candidates = 0
batch_num = 0


@mcp.tool(name="next")
def next() -> dict | str | None:
    """Returns the next orphaned subdivision and its candidates. Repeated calls paginate through the candidates until all candidates have been processed.

    Candidates are flat formatted: { geonames_id: "name1, name2 - [admin_level]", ... }
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

    orphan["candidates"] = candidates

    batch_num += 1
    processed_candidates += len(orphan["candidates"])
    return orphan


@mcp.tool(name="merge")
def merge(candidate_geonames_id: str) -> str:
    """Merges an orphaned subdivision into an existing country candidate.

    Args:
        candidate_geonames_id (str): The geonames_id of the geonames subdivision to merge into.
    """
    orphan = get_next_orphan()
    if orphan is None:
        return "ERROR: NO ORPHAN TO MERGE"

    iso_code = orphan["iso_code"]

    geonames_id = int(candidate_geonames_id)

    is_valid, msg = is_valid_candidate(iso_code, geonames_id)
    if not is_valid:
        return msg

    candidate = get_geonames_submap().get(geonames_id=geonames_id)
    candidate.iso_code = iso_code

    write_resolution(iso_code, geonames_id)
    pop_orphan(iso_code)

    log_decision(
        f"MERGE  {iso_code}  {orphan['name']!r} -> {candidate_geonames_id} {candidate.name!r}"
    )

    global batch_num
    batch_num = 0

    return "SUCCESS"


@mcp.tool(name="add")
def add() -> str:
    """Adds an orphaned subdivision as a new entry."""

    orphan = get_next_orphan()

    if orphan is None:
        return "ERROR: NO ORPHAN TO ADD"

    write_resolution(orphan["iso_code"], None)
    pop_orphan(orphan["iso_code"])

    log_decision(f"ADD    {orphan['iso_code']}  {orphan['name']!r}")

    global batch_num
    batch_num = 0

    return "SUCCESS"


@mcp.tool(name="review")
def review() -> str:
    """Dumps the next orphan and all its candidates to review_output.json for the user to manually review and decide on the resolution. Prompt the user to call add or merge (with the selected geonames_id)"""

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
