---
name: resolve-subdivisions
description: Resolves ISO 3166-2 subdivisions that localis's data-ingestion pipeline flagged as orphaned; ones fuzzy-matching couldn't confidently merge with a GeoNames counterpart. Uses real-world geographic knowledge (transliteration variants, historical or colloquial name changes, language variants) to pick the correct match with high confidence, or explicitly escalates genuinely ambiguous cases to a human instead of guessing.
disallowed-tools: Bash Read Grep Glob Edit Write Agent WebFetch
---

# Resolve Subdivisions

## Instructions

### Step 1. Retrieve the next orphaned subdivision
**CALL** the `next` tool to retrieve the next orphaned ISO subdivision and its *top-tier* candidates.

- If `next` returns `null`, **STOP**. We've reached the end of the orphaned subdivisions list.
- If `next` returns "MAX CANDIDATES REACHED...", follow the instructions provided in that message verbatim. The user must reset the process as instructed.

### Step 2. Resolve the orphaned subdivision
- Use real-world knowledge, not string similarity.
- If multiple candidates share a name, use the candidate's `admin_level` against the orphan's `type` to pick the right one, not just the first match.

**IF** you have high confidence that this ISO subdivision and one specific candidate are the same place (a transliteration difference, an old vs. current name, a local vs. official form, etc.):
  1. **CALL** the `merge` tool with `iso_code`, `geo_sub_hashid` and any additional names if applicable.
  2. Return to Step 1.

**IF** none of the *top-tier* candidates fit:
  1. **CALL** the `next` tool with `return_all=True` to retrieve all remaining candidates for the orphaned subdivision.
  2. Rerun Step 2 with the full list of candidates.

**IF** none of the full candidate list fits either:
  1. Proceed to Step 3. Do not proceed to Step 4 without first making an actual Websearch tool call for this orphan in this turn. If no such call has been made yet, make it now.

### Step 3. Escalate to Websearch
**CALL** the `Websearch` tool with the orphan's name and ISO code to gather additional information about the orphaned subdivision.

**IF** a confident match is found after the websearch:
  1. **CALL** the `merge` tool with `iso_code`, `geo_sub_hashid` and any additional names if applicable.
  2. Return to Step 1.

**IF** no confident match is found after the websearch:
  1. Proceed to Step 4.

### Step 4. Add as a new entry
**IF** none of the candidates fit, but the orphaned subdivision is a confirmed and valid entity:
  1. **CALL** the `add` tool with `iso_code` and any additional names if applicable.
  2. Return to Step 1.

**IF** the orphaned subdivision is not a valid entity, cannot be matched to any existing candidates, is too ambiguous to resolve, or you have otherwise conflicting or insufficient information:
  1. Proceed to Step 5.

### Step 5. Escalate for human review
**CALL** the `review` tool to dump the orphan to `review_output.json` for the user to review and make a decision. Offer the user the following two options along with a link to open the `review_output.json` in the IDE:
  1. Add the orphan as a new entry.
  2. Merge the orphan with an existing candidate by inputting the hashid.

## Guardrails
- Never fabricate a `hashid` — it must come from that specific entry's own `candidates` list; `merge` validates this and raises if it wasn't.

