---
name: resolve-subdivisions
description: Resolves ISO 3166-2 subdivisions that localis's data-ingestion pipeline flagged as orphaned; ones fuzzy-matching couldn't confidently merge with a GeoNames counterpart. Uses real-world geographic knowledge (transliteration variants, historical or colloquial name changes, language variants) to pick the correct match with high confidence, or explicitly escalates genuinely ambiguous cases to a human instead of guessing.
disallowed-tools: Bash Read Grep Glob Edit Write Agent WebFetch
---

# Resolve Subdivisions

## Reading the orphan and its candidates

`next` returns the orphan's `iso_code`, `name`, `aliases`, `country`, `type` and `admin_level`, plus a batch of `candidates`.

Candidates come from every GeoNames subdivision in the orphan's country, sorted by name similarity, with candidates at the orphan's own level first on ties. Each is formatted `geonames_id: "name, aliases - [admin_level]"`, for example `1668352: "Tainan, 台南市, 臺南市 - [2]"`, with two optional suffixes:
- `CLAIMED BY <iso_code>`: another ISO subdivision already holds this record. You can never merge into it.
- `(note)`: for some orphans, the first batch holds only the specific records automerge flagged, either "automerge's pick" (a match just over the threshold that needs confirming) or "automerge's contested target" (a record several ISO subdivisions matched equally well). The batch after it is the regular top-tier batch. A note can also read "type mismatch": the GeoNames name contains a word like "City" that suggests a different kind of place than the ISO type. That is sometimes a real difference (a city vs. the region around it) and sometimes just naming (Hamburg is both a city and a German state), so judge which before merging.

A `wikidata_conflict` orphan is an earlier skill decision that disagrees with Wikidata's mapping. `next` includes it as `current_decision` (its `geonames_id`, or "add as-is", and its `reason`), and its first batch holds the two records in question, noted "Wikidata's mapping" and "current skill decision". Wikidata agrees with independent checks over 99% of the time, so keep the current decision only if you can say concretely why Wikidata's record is wrong (a different place, the wrong level, a populated place rather than the administrative unit). Either way, `merge` with the record you choose, or `add` to keep an "add as-is" decision, giving that explanation as the `reason`.

ISO and GeoNames sometimes disagree on a subdivision's level (a city ISO lists at level 1 can sit at level 2 in GeoNames), so a candidate at a different level can still be the right one. Use the level to tell apart same-name candidates, such as a city and the county named after it, not to rule candidates out.

## Instructions

### Step 1. Retrieve the queued orphan
Call the `next` tool to retrieve the queued orphaned ISO subdivision and its first batch of candidates.

If `next` returns `null`, stop. We've reached the end of the orphaned subdivisions list.

If `next` returns "MAX CANDIDATES REACHED...", follow the instructions in that message verbatim. Do not report session progress.

If `next` returns an empty candidates array, proceed to Step 3.

### Step 2. Check the top-tier candidates
The top-tier batch is the first batch, or the second batch if the first held only flagged records (call `next` once more to get it, after checking the flagged records).

Use real-world knowledge, not string similarity. If iterating over candidates of the same country as the previous orphan, you can use that previous context to inform your decision.

If you have high confidence that this ISO subdivision and one specific unclaimed candidate are the same place (a transliteration difference, an old vs. current name, a local vs. official form, etc.), call the `merge` tool with `candidate_geonames_id` and a `reason`, one sentence naming what makes them the same place, then return to Step 1. Every merge needs a reason: it's the record a later audit works from, and if you can't state one, you aren't confident enough to merge.

Otherwise, including when the matching place is `CLAIMED BY` another ISO code or when two or more candidates plausibly fit, proceed to Step 3.

### Step 3. Research
Call the `Websearch` tool once, using only the orphan's `name` and `iso_code`. Do not add other search terms. Learn what the place is: its other current and former names, the region it belongs to, and its administrative level.

If the search identifies one specific unclaimed candidate you've already seen as the same place, call `merge` with `candidate_geonames_id` and a `reason` naming what the search showed (e.g. a former name), then return to Step 1.

If the search confirms the matching place is `CLAIMED BY` another ISO code, or can't decide between two or more plausible candidates, proceed to Step 6.

Otherwise, proceed to Step 4.

### Step 4. Check the remaining candidates
Call `next` repeatedly to page through the remaining batches, checking each against what the search taught you. A place listed under an old or local name can appear in any batch.

If you find one specific unclaimed candidate that is the same place, call `merge` with `candidate_geonames_id` and a `reason` naming what connects them, then return to Step 1.

If you find the same place `CLAIMED BY` another ISO code, or two or more plausible candidates you can't tell apart, proceed to Step 6.

If `next` returns an empty candidates array, proceed to Step 5.

### Step 5. Decide whether the place has no GeoNames counterpart
Call the `add` tool only if the search confirmed the orphan is a real, current or historical entity and one of these reasons applies. Give the reason that applies, with the specifics, as the `reason`, then return to Step 1.

1. **GeoNames uses a different administrative scheme for the country**, so this kind of subdivision doesn't exist in GeoNames at all. Examples: GeoNames lists Madagascar's 22 regions while ISO lists its 6 provinces. GeoNames keeps London's boroughs at admin level 3, below Greater London, and localis only ingests levels 1 and 2. GeoNames has no administrative record for Hungary's cities with county rights, only populated places; never merge such a city into its járás, which is a larger district.
2. **GeoNames treats the place as its own country.** ISO lists some territories as a country's subdivisions while also giving them their own ISO 3166-1 code, and GeoNames files them only as countries: France's overseas departments and collectivities, the US's outlying areas (Guam, Puerto Rico, etc.), Curaçao, Aruba and Sint Maarten under the Netherlands. For these, check only the top-tier batch; if nothing matches, `add` without searching or paging further.
3. **A real reorganization retired the subdivision.** It was merged into or split into other subdivisions, ISO still lists it, and GeoNames has no record of the retired subdivision itself (only its successors). If GeoNames still has a record for the retired subdivision, `merge` into that instead. A simple rename isn't a retirement: the renamed place is still there to merge with.
4. **Disputed territory.** ISO lists the subdivision under one country, while GeoNames files that land under another (Serbia's Kosovo districts, which GeoNames places under Kosovo). Add it as ISO lists it, without taking a side.

Otherwise, proceed to Step 6. "None of the candidates matched" is not a reason to `add`, and neither is a place being too new for GeoNames: an `add` is permanent and becomes a duplicate once GeoNames includes the place.

### Step 6. Escalate for human review
Escalate whenever any of these is true:
- The matching record exists but is `CLAIMED BY` another ISO code.
- Two or more candidates plausibly fit, and level, type and the web search can't decide between them.
- The web search shows the orphan, a current subdivision, maps to only part of a GeoNames record or to several of them, and none of Step 5's reasons explains it.
- No candidate matches, and none of Step 5's reasons explains the absence.

Call the `review` tool with a `reason` stating which of the above applies and what the web search found. That reason is stored with the user's eventual decision as its audit record, so make it complete. Report your findings to the user and offer them the following two options, then stop this turn and wait for the user to respond:
1. `Add` the orphan as a new entry.
2. `Merge` the orphan with an existing candidate by inputting the geonames_id.

When the user decides, apply their decision: call `merge` with the `geonames_id` they chose, or call `add`, passing the user's explanation as the `reason` either way. The decision is recorded as the user's automatically. Then return to Step 1.

## Guardrails
- **Never fabricate a `geonames_id`.** It must come from that specific entry's own `candidates` list.
- **Never merge into a `CLAIMED BY` candidate.**
- When unsure between `add` and escalating, escalate. A wrong `add` creates a duplicate record that ships silently; an escalation costs one human decision.
- **This document is the only source of rules.** Don't apply decision rules remembered from earlier sessions, and don't save new ones to memory. A user's ruling on an escalation applies to that orphan; if the user says it covers similar orphans, it holds for the rest of this session only, and they'll add it here if it should last. When a case resembles an earlier decision but isn't covered here, escalate and mention the resemblance.
