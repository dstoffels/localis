---
name: resolve-subdivisions
description: Resolves ISO 3166-2 subdivisions that localis's data-ingestion pipeline flagged as orphaned; ones fuzzy-matching couldn't confidently merge with a GeoNames counterpart. Uses real-world geographic knowledge (transliteration variants, historical or colloquial name changes, language variants) to pick the correct match with high confidence, or explicitly escalates genuinely ambiguous cases to a human instead of guessing.
disallowed-tools: Bash Read Grep Glob Edit Write Agent WebFetch
---

# Resolve Subdivisions

## Instructions

### Step 1. Retrieve the queued orphan
**CALL** the `next` tool to retrieve the queued orphaned ISO subdivision and its next batch of candidates.
**IF** `next` returns `null`, **STOP**. We've reached the end of the orphaned subdivisions list.

**IF** `next` returns "MAX CANDIDATES REACHED...", follow the instructions provided in that message verbatim. DO NOT report session progress.

**IF** `next` returns an empty candidates array, proceed to Step 3.

**IF** `next` returns a valid orphaned subdivision with candidates, proceed to Step 2.

### Step 2. Resolve the orphaned subdivision with a candidate
- Use real-world knowledge, not string similarity.
- If multiple candidates share a name, use the candidate's `admin_level` against the orphan's `type` to pick the right one, not just the first match.
- If iterating over candidates of the same country as the previous orphan, you can use that previous context to inform your decision, especially with large numbers of subdivisions within that country.

**IF** you have high confidence that this ISO subdivision and one specific candidate are the same place (a transliteration difference, an old vs. current name, a local vs. official form, etc.):
  1. **CALL** the `merge` tool with `candidate_geonames_id`.
  2. Return to Step 1.

**IF** none of the candidates fit:
  1. Return to Step 1 to retrieve the next batch of candidates for the orphan.

### Step 3. Research, then decide
**IF** none of the candidates fit, **CALL** the `Websearch` tool using only the orphan's `name` and `iso_code` before deciding anything. DO NOT add additional search terms. Never `add` without searching first, no matter how confident you feel.

**IF** the websearch reveals a certain match, that you have high confidence this ISO subdivision and a specific candidate are the *same place*:
  1. **CALL** the `merge` tool with `candidate_geonames_id`.
  2. Return to Step 1.

**IF** no confident match is found, but the websearch confirms the orphan is a valid, current or historical entity:
  1. **CALL** the `add` tool.
  2. Return to Step 1.

**ELSE**: Proceed to Step 4.

### Step 4. Escalate for human review
**CALL** the `review` tool to dump the orphan to `review_output.json` for the user to manually review and make a decision. Offer the user the following two options along with a link to open `review_output.json` in the IDE and then STOP this turn and wait for the user to respond:
  1. `Add` the orphan as a new entry.
  2. `Merge` the orphan with an existing candidate by inputting the geonames_id.

## Guardrails
- Never fabricate a `geonames_id`, it must come from that specific entry's own `candidates` list

