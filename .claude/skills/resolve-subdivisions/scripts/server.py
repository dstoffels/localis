import json
from typing import Literal
from utils import get_candidates, get_geonames_submap, get_next_orphan, is_stale, is_valid_candidate, pop_orphan, reload_if_stale, write_resolution
from mcp.server import MCPServer

mcp = MCPServer(name="resolve-subdivisions")

# Session context budget, in estimated tokens. The server only sees its own output, so the estimate adds fixed allowances for the agent's reasoning and web searches; calibrated from a 44-orphan session that used ~1.1k tokens per mostly-easy orphan.
TOKEN_BUDGET = 150_000
CHARS_PER_TOKEN = 4
ORPHAN_ALLOWANCE = 1_000
SEARCH_ALLOWANCE = 3_000
estimated_tokens = 0
batch_num = 0
escalated_iso_code: str | None = None
escalation_findings: str | None = None
# returned by merge and add when another process wrote resolution_map.json since this server read it
STALE = "ERROR: resolution_map.json changed outside this session (a new ingest, or another session's decision); call next_orphan to reload, then decide this orphan again"


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


@mcp.tool(name="next_orphan")
def next_orphan() -> dict | str | None:
    """Returns the next orphaned subdivision and its candidates. Repeated calls paginate through the candidates until all candidates have been processed.

    Candidates are a list, best match first, each formatted "geonames_id: name1, name2 - [admin_level] CLAIMED BY <iso_code> (note)", where "CLAIMED BY" and the note appear only when they apply.
    """
    global estimated_tokens, batch_num

    # a fresh ingest or another session's decision restarts the current orphan against the file as it now stands
    if reload_if_stale():
        _finish_orphan()

    # only checked between orphans (batch_num == 0), never mid-orphan, so a reset never splits an orphan's candidates across sessions
    if estimated_tokens >= TOKEN_BUDGET and batch_num == 0:
        estimated_tokens = 0
        return "CONTEXT BUDGET REACHED: Tell the user to call /clear to reset session context and then cease all further processing in this session."

    orphan = get_next_orphan()
    if orphan is None:
        return None

    orphan["candidates"] = get_candidates(orphan["iso_code"], batch_num)

    estimated_tokens += len(json.dumps(orphan, ensure_ascii=False)) // CHARS_PER_TOKEN
    if batch_num == 0:
        estimated_tokens += ORPHAN_ALLOWANCE
    elif batch_num == 1:
        # paging past the first batch means the top tier didn't settle it, so the agent searched
        estimated_tokens += SEARCH_ALLOWANCE

    batch_num += 1
    return orphan


@mcp.tool(name="merge")
def merge(candidate_geonames_id: str, reason: str) -> str:
    """Merges the current orphan into a GeoNames candidate from its country.

    Args:
        candidate_geonames_id (str): The geonames_id of the geonames subdivision to merge into.
        reason (str): One sentence on why the candidate is the same place, e.g. "transliteration of Krasnodarskiy kray", "former name, renamed 2019", or the user's explanation after a review.
    """
    if is_stale():
        return STALE
    orphan = get_next_orphan()
    if orphan is None:
        return "ERROR: NO ORPHAN TO MERGE"

    iso_code = orphan["iso_code"]

    if not candidate_geonames_id.strip().isdigit():
        return "ERROR: Invalid candidate: the geonames_id must be the number at the start of a candidate's entry"
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
    if is_stale():
        return STALE
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
