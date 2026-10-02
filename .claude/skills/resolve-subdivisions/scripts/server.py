from typing import Literal
from utils import *
from mcp.server import MCPServer

mcp = MCPServer(name="resolve-subdivisions")

MAX_CANDIDATES = 1000
processed_candidates = 0
batch_num = 0
escalated_iso_code: str | None = None
escalation_findings: str | None = None


def _decided_by(iso_code: str) -> Literal["agent", "human"]:
    """An orphan resolved after `review` escalated it was decided by the human."""
    return "human" if iso_code == escalated_iso_code else "agent"


def _escalation(iso_code: str) -> str | None:
    return escalation_findings if iso_code == escalated_iso_code else None


def _finish_orphan() -> None:
    global batch_num, escalated_iso_code, escalation_findings
    batch_num = 0
    escalated_iso_code = None
    escalation_findings = None


@mcp.tool(name="next")
def next() -> dict | str | None:
    """Returns the next orphaned subdivision and its candidates. Repeated calls paginate through the candidates until all candidates have been processed.

    Candidates are flat formatted: { geonames_id: "name1, name2 - [admin_level] CLAIMED BY <iso_code> (note)", ... }, where "CLAIMED BY" and the note appear only when they apply.
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
def merge(candidate_geonames_id: str, reason: str) -> str:
    """Merges an orphaned subdivision into an existing country candidate.

    Args:
        candidate_geonames_id (str): The geonames_id of the geonames subdivision to merge into.
        reason (str): One sentence on why the candidate is the same place, e.g. "transliteration of Krasnodarskiy kray", "former name, renamed 2019", or the user's explanation after a review.
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

    write_resolution(iso_code, geonames_id, reason, _decided_by(iso_code), _escalation(iso_code))
    pop_orphan(iso_code)
    _finish_orphan()

    return "SUCCESS"


@mcp.tool(name="add")
def add(reason: str) -> str:
    """Adds an orphaned subdivision as a new entry with no GeoNames counterpart.

    Args:
        reason (str): The concrete reason GeoNames has no record for this place, e.g. "GeoNames uses Madagascar's 22 regions, not ISO's 6 provinces". "No candidate matched" is not a reason.
    """

    orphan = get_next_orphan()

    if orphan is None:
        return "ERROR: NO ORPHAN TO ADD"

    write_resolution(orphan["iso_code"], None, reason, _decided_by(orphan["iso_code"]), _escalation(orphan["iso_code"]))
    pop_orphan(orphan["iso_code"])
    _finish_orphan()

    return "SUCCESS"


@mcp.tool(name="review")
def review(reason: str) -> str:
    """Escalates the current orphan to the user for a decision. The findings are stored with whatever decision the user makes, so report them in full to the user, then apply their decision with merge or add.

    Args:
        reason (str): Why this orphan needs a human decision, including what the web search found.
    """

    orphan = get_next_orphan()

    if orphan is None:
        return "NO ORPHANS TO REVIEW"

    global escalated_iso_code, escalation_findings
    escalated_iso_code = orphan["iso_code"]
    escalation_findings = reason

    return "SUCCESS"


if __name__ == "__main__":
    mcp.run(transport="stdio")
