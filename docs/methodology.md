# Subdivision Pipeline

## Scope

`localis`'s subdivision dataset reconciles two independent sources that don't share a common identifier: ISO 3166-2 (via Debian's iso-codes project) and GeoNames' `admin1CodesASCII.txt`/`admin2Codes.txt`. This document is a complete, falsifiable account of how an matched ISO and GeoNames entries become one shipped `Subdivision` record, every gate the pair must pass, the specific failure mode each gate exists to prevent, with real examples that surfaced that failure mode. Anyone who finds a result they don't trust should be able to trace it back to the reasoning that produced it here. 

A list of currently unmerged subdivisions can be found in [unmerged_subdivisions.md](unmerged_subdivisions.md), some genuinely have no GeoNames counterpart, while others may simply not yet have been reconciled by the pipeline, resulting in the potential for duplicates entries in the `localis` dataset. We welcome contributions and corrections from users who identify discrepancies or missing matches.

## Source provenance

ISO 3166-2 is the authority for a subdivision's official name, administrative type, and its real administrative hierarchy. GeoNames is the authority for a stable numeric identifier (`geonames_id`), the `geonames_code` (its own admin1/admin2 code string, e.g. `US.CA`, not FIPS), and a large alternate-name corpus. Where the two sources disagree, ISO's structure wins and GeoNames supplies enrichment. Ipregistry's `iso3166` repository contributes its `localVariant` column to aliases where available.


## Parsing GeoNames subdivisions

GeoNames' `admin1CodesASCII.txt` and `admin2Codes.txt` are parsed first (51,508 in total), extracting the country code from the `geonames_code` and then alternate names are added to each subdivision's alias list. GeoNames already buckets the admin-level entries by file, so we assign the `admin_level` for GeoNames entries accordingly. If the entry is merged with an ISO counterpart downstream, the ISO `admin_level` will override the source value.


### Alias enrichment
Aliases are enriched from GeoNames' `alternateNamesV2.txt`, filtered to English plus the official language(s) of subdivision's country (from Unicode CLDR's `territoryInfo.json`), excluding any alternate name flagged historic or colloquial or duplicate. GeoNames' alt-names list is comprehensive, with dozens of multi-language names for many entries. Thus we filter in only the two language criteria to maintain a smaller storage footprint, but aim to provide translation/language support in future versions to bridge this gap.

Alias enrichment is applied before attempting to merge with ISO counterparts, so the extra name variants are also available for fuzzy comparison, not just to provide them in the shipped dataset.

## Parsing ISO subdivisions

All 5046 ISO subdivisions are initially loaded alongside the parsed GeoNames dataset, where two things happen before any matching begins: bracket/parenthetical splitting, and admin-level classification.

### Bracket/parenthetical splitting
ISO entries occasionaly suffix their name with bracketed or parenthetical content. That content is one of three things: a genuine alternate name (`"Girona [Gerona]"`), a bare subdivision code (`"Stockholms län [SE-01]"`), or a territory-dispute/type annotation (`"Aousserd (EH)"`, `"Amānat al 'Āşimah [city]"`). Left inline, this actively broke fuzzy matching: `"Stockholms län [SE-01]"` normalizes to `"stockholms lan se 01"`, three junk tokens away from GeoNames' bare `"Stockholms"`. `_split_bracketed_name()` splits the primary name from the bracket content at load time: a genuine alternate name becomes an alias, everything else (a bare code, a duplicate of the primary name, a known non-name annotation) is discarded.

### Admin-level classification
 `admin_level` is computed independently for ISO-sourced entries using a recursive walk of ISO's own parent-code chain. Each entry's level is 1 plus the number of real (non-bypassed) ancestors above it, so depth isn't capped at 2; it falls out naturally from however deep a country's actual ISO nesting goes. 
 
`admin_level` is observed from 0-3 across the current dataset, though nothing caps it there, a deeper country would simply compute a higher level:
- 0 represents **non-administrative exceptions**
- 1 represents top-level administrative divisions under the country
- 2 represents second-level divisions (e.g., counties or districts)
- 3 is the deepest level observed so far, and exists within the ISO hierarchy (France)

#### Non administrative exceptions
- Indonesia's ISO table groups its 38 real provinces under 7 "Geographical unit" entries, a pure island-based organizing category with its own government precisely nowhere
- The Dominican Republic groups its 31 provinces plus the Distrito Nacional (32 total) under 10 "Region" entries that are a statistical/regional-planning construct (no governor, no budget, no elected body)
- Cabo Verde's 22 municipalities are similarly grouped under two "Geographical region" entries (the Barlavento/Sotavento island groups).
- Ireland's ISO table groups its 26 counties under 4 "Provinces" entries, a purely ceremonial division with no government of its own.
- Iceland's ISO table groups its 64 municipalities under 8 "Region" entries, a statistical construct with no government of its own.
- Lithuania's ISO table groups its 60 municipalities under 10 "County" entries, which no longer have any governing authority since 2010.
- Malawi's ISO table groups its 28 districts under 3 "Region" entries, a purely statistical division with no government of its own.

These exceptions are enumerated in `resolution_map.json`'s `NON_ADMINISTRATIVE_TYPES` as a rule, rather than a per-code list, so it stays correct even as new entries matching that pattern are added to ISO's data in the future. An entry matching this rule is loaded with `admin_level=0`, keeping its true ISO `parent` reference (the relationship is real and documented, even though the parent isn't a government). They bypass GeoNames matching entirely, since by construction, nothing in GeoNames' admin1/admin2 files could ever represent "Sumatera" or "Ozama" as a governed place. 

Their real children (Irish counties, Icelandic municipalities, Lithuanian municipalities, etc.) are unaffected by the exclusion and correctly compute `admin_level=1`.

The standard for adding a country here is deliberately two-part, structural signal and an independently verifiable governing-function fact. Two structurally similar candidates were checked and rejected to demonstrate the bar isn't rubber-stamped. Guinea-Bissau's `Province → Region` nesting (3 provinces, `GW-L`/`GW-N`/`GW-S`, each genuinely parenting several `Region`-type entries) and Iraq's `Region` (the Kurdistan Region, `IQ-KR`, containing 3 real governorates) both carried the same shape from the raw parent-usage data alone, but both tiers are real, separately governed administrative bodies in those countries, not documentation categories, so no exception was made.

## The Merge Pipeline
`resolution_map.json` is the single source of truth for every subdivision's merge resolution in the pipeline, merged in three sequential stages: `skill_resolved`, `wikidata_merge` and `automerge`. Only whatever's left after the first two stages goes through the `automerge` gates at all. An agentic, human or wikidata-based decision can never lose its merge target to a fresh automated merge, because automerge never gets the chance to compete for it in the first place.

Nothing in `resolution_map.json` needs a manual cache-invalidation step regardless of which bucket produced it: every run recomputes `auto_merge` and `wikidata_merge` fresh and reconciles each against `audited` (the record of entries an audit has independently verified), keeping an audited entry only if the fresh result still agrees with it and otherwise evicting the stale record and re-opening it for review. A methodology change like the one described in Fuzzy match scoring, or a change on Wikidata's own end, therefore surfaces its own affected entries automatically on the next run, rather than requiring something to remember which decisions need re-checking. `skill_resolved` decisions are the one exception: they're permanent until a human revisits them, since a human decision isn't a function of either algorithm and has nothing to "go stale" against.

### 1. resolve-subdivisions Skill
The `resolve-subdivisions` skill is an MCP-backed Claude skill that assists in resolving orphaned subdivisions by agentic reasoning, websearch escalation and finally, human intervention.

`skill_resolved` holds decisions made by the `resolve-subdivisions` skill, which is actually a branch of the merge pipeline. Any attempted merges that do not pass the initial wikidata and automerge gates are "**orphaned**" and the pipeline exits before dumping to the final dataset. This signals the need for human intervention, where the `resolve-subdivisions` skill is invoked. The full ingest pipeline cannot complete until all orphans have been resolved.

#### Orphans
Orphans are categorized in three different buckets and handled differently:
- `ambiguity`: entries for which the pipeline found multiple, close-matching GeoNames candidates. Only the ambiguous GeoNames candidates discovered in automerge are presented to the agent initially. After which the country/admin-level-filtered GeoNames candidates are presented. This is typically resolved in the first round.
- `no_candidates`: entries for which the pipeline could not find any GeoNames candidates at all. The agent is exposed to *all* of a country's GeoNames subdivisions, instead of filtering by admin level. These typically result in an unmerged ISO entry. 
- `no_matches`: entries for which the pipeline could not find any matching GeoNames candidate. The agent is fed a batched list of fuzzy-sorted GeoNames candidates to choose from.

> An initial wikidata cross-check was performed to validate the consistency of the `resolve-subdivisions` skill and found 701/702 (99.9%) agreements in the iso_code-geonames_code mappings.

### 2. Wikidata

`wikidata_subdivisions.py` queries Wikidata's SPARQL endpoint for every item carrying both P300 (ISO 3166-2 code) and P1566 (GeoNames id), keeping only ISO codes with exactly one claimed `geonames_id` (no ambiguous multi-claim codes). A merge is only applied if that `geonames_id` actually exists in our GeoNames-sourced data and belongs to the same country as the ISO code; anything else falls through to automerge instead. This source covers 4322 ISO codes unambiguously. 

Before implementation, every unambiguous match was checked against the pipeline's existing decisions: 4134 of 4147 overlapping codes agreed (99.7%), and a 25-entry random sample of the net-new codes it could resolve came back 25/25 correct. Once live, it resolved roughly 3861 subdivisions on its own, cutting what automerge needs to handle and subsequently yielded far fewer orphans. The remaining disagreements between Wikidata and the rest of the pipeline are almost entirely one specific, already-understood pattern: GeoNames frequently has two separate records for the same place, typically an administrative-boundary record (what `admin1CodesASCII.txt`/`admin2Codes.txt` actually contain), and Wikidata's P1566 occasionally links to the latter. 

Checking every disagreement across the dataset, 142 of 144 were exactly this, a populated-place id that doesn't exist in our admin1/2 data at all and so is already rejected by the validation above, confirmed systematically for Hungary's "city with county rights" subdivisions and the Marshall Islands' municipalities, where every single entry in both groups showed this pattern. **Exactly one genuine competing claim remains in the entire dataset**: `RU-AL`/`RU-ALT` (Altai Republic/Altai Krai, two real, easily-confused Russian federal subjects), where both the pipeline's answer and Wikidata's answer are valid admin1 ids, just swapped relative to each other. This pair has now surfaced independently four separate times across unrelated checks this session (the original type-family disqualification work, the lowest-margin cusp audit, and this crosswalk check twice), which is a stronger signal than any single disagreement would be, and is the one open item for audit.

### 3. automerge

Whatever resolve-subdivisions and Wikidata didn't already resolve funnels into `automerge`. Geonames candidates are compared to ISO subdivisions in buckets filtered by `country` and `admin_level`, so an ISO entry is only ever compared against GeoNames entries of the same country and the same administrative level. The admin level is capped at 2 since GeoNames never nests deeper (so ISO's level-2 and level-3 entries draw from and compete over the same GeoNames pool). A pair has to clear every gate below, in order, before it's eligible to merge.

### 1. Type-family disqualification

A pair can pass every other gate and still be wrong if the two sides disagree on the most basic distinction: is this the settlement itself, or the area around it? `UA-30` (ISO: "Kyiv", the city) automerged with GeoNames' `UA.13`, whose own alternate names are exclusively `Kyiv Oblast`/`Kyivshchyna`, the surrounding oblast, not the city. It won purely on string score, "Kyiv" against bare "Kyiv" is a near-perfect match, while `UA-32` ("Kyivska oblast", the actual oblast) never scored well enough against the same bare name to even compete. The same shape recurred for Vilnius (`LT-58` grabbing the GeoNames entry whose own alias literally says "Vilnius City Municipality") and, per a cached-resolution conflict the pipeline logged, for Altai (`RU-ALT` vs. `RU-AL`).

The fix disqualifies a candidate pair before scoring if GeoNames' raw, unstripped name or aliases carry a qualifier word from a different family than the ISO side's own `type`. The families are deliberately coarse: just `city` (city/shi/si/gorodskoy/town) against everything else (`area`). An earlier, finer-grained version (separate families for province/department/county/region/etc.) was tried and reverted after it broke real matches: GeoNames' raw name for Romanian counties is literally `"Vâlcea County"` while ISO types them `"Department"`, and Sweden's `"län"` had been miscategorized into the wrong family entirely. These are the same real-world administrative tier described by different translation conventions, not genuinely different tiers, so treating them as mutually exclusive produced false disqualifications across nearly all of Romania and Sweden. Collapsing back to just city-vs-area eliminated that regression (a drop of 150 wrongly-orphaned entries on the run this was fixed). Settlement-vs-area is the one distinction that held up under scrutiny; finer administrative-type distinctions did not.

### 2. Name normalization and noise-token stripping

A pair that survives type-family disqualification is then normalized for comparison: both sides' names and aliases are lowercased, diacritics-normalized, and stripped of a fixed set of administrative qualifier words (`NOISE_TOKENS`), so a match isn't penalized just because one side spells out "Province" and the other doesn't. The set spans dozens of languages' equivalent words by inspecting GeoNames' actual raw admin1/admin2 name text for recurring trailing/leading qualifier words. All names were dumped to a dict with their counts to identify the common patterns.

### 3. Fuzzy match scoring

Scoring uses `token_sort_ratio` against a dynamic threshold: base 90, reduced 15 points for names averaging ≤5 characters, 10 points for ≤8, 5 points for ≤12. Short names need proportionally more tolerance, since the same absolute edit distance matters less as a fraction of a longer string. `token_sort_ratio` replaced `token_set_ratio` specifically because `token_set_ratio` treats a full token-subset relationship as automatically near-100% similar, which is correct for a genuine noise-word difference but wrong for administrative qualifiers naming genuinely different real places ("Val-de-Marne" is not "Marne"). A directional-token check (`has_directional_mismatch`) separately vetoes any pair split only by north/south/east/west/upper/lower/central, preventing "East Germany" from ever matching "West Germany" regardless of score.

An earlier version of this function also discounted single-token names a further 5 points, on top of the length discount. That stacked discount was removed after auditing the lowest-margin merges turned up confirmed false positives sitting exactly at the resulting threshold: `GB-ENF` "Enfield" matched GeoNames' alt-name-enriched short form "Wakefield" at a score of exactly 75 against a threshold of exactly 75, two unrelated English places sharing only a common "-field" suffix with zero overlap at the start of either word. The same audit found `GB-EAL` "Ealing"/"Reading", `PL-16` "Opolskie"/"Podlasie", and two Vietnamese province pairs (`VN-31`, `VN-32`) sitting in the same knife-edge pattern. Removing the discount pushed roughly 16 previously-correct transliteration/grammatical-variant matches (e.g. Panjshayr/Panjshir, Kordestān/Kurdistan, several Russian oblasts' grammatical-case endings) into orphan status in exchange for closing 5-7 confirmed false positives; given a false merge ships silently as fact while an orphan is a recoverable, flagged gap, that trade was taken deliberately.

### 4. Ambiguity threshold

Once every pair in a bucket is scored, candidate targets are checked for collisions before any assignment happens: if two or more distinct ISO subdivisions both score at or above 90 against the same GeoNames target, that target is excluded from automerge entirely rather than handed to whichever one scored marginally higher. This catches namesake collisions, most often a city and its own containing district sharing an identical bare name, where string similarity genuinely cannot break the tie without an external signal. Excluded targets are logged (`"ambiguous target '...': ... all scored >= 90, excluding from automerge"`) and their ISO subdivisions fall through to the human resolution path below.

### 5. Global best-score assignment

With ambiguous targets already excluded, every remaining candidate pair is claimed in descending score order (`scored_pairs.sort(...)`), so a strong match can never be blocked by a weaker one that happened to get claimed first due to iteration order.

**Whatever survives all of the above unmerged** is an orphan, handed to the `resolve-subdivisions` skill, which reuses the exact same `candidate_pool()`/`score_candidates()` primitives (type/directional filtering included) so it never shows a candidate the pipeline's own rules would already refuse

## Known limitations

- **The Philippines is not actually a non-administrative case, on reflection, and is noted here to record why it was ruled out rather than left ambiguous.** Its 17 `Region` entries parenting provinces look structurally identical to the confirmed cases, but the distinguishing test isn't "does this tier have its own separately-elected government," it's "does this tier have any administrative function at all." The confirmed cases (Indonesia, DR, Cabo Verde, Ireland, Iceland, Lithuania) are pure labels with zero governing apparatus. Philippine regions, including the ~14-15 without full autonomy, have real administrative function: Regional Development Councils, and national government agencies organizing field operations and budgets by region. That's the same shape as Guinea-Bissau's `Province → Region` or Iraq's Kurdistan Region, both already correctly excluded for the same reason, real governing apparatus, just not uniformly autonomous. Region=admin_level 1, Province=admin_level 2 is correct as-is for all 17 regions, ARMM and CAR included.
- **`RU-AL`/`RU-ALT` is an open, unresolved discrepancy**: Wikidata and the pipeline disagree on which of two real GeoNames ids belongs to Altai Republic versus Altai Krai, and this is the only genuine competing claim found anywhere in the cross-validated dataset. Needs direct research, not another automated check, since both sources are self-consistent and the dispute is specifically about which one is right.
- **`TW-TNN`/`MG-D` are confirmed false positives with no correcting patch applied yet**: `TW-TNN` (Tainan) merged to a GeoNames record reflecting an outdated 4-province Taiwan structure rather than the correct modern entry; `MG-D` (Antsiranana) merged to Atsinanana, two genuinely different Madagascar divisions sharing a coincidental naming resemblance. Both were found auditing the cusp right after the single-token threshold discount was removed (Fuzzy match scoring). The fix is a one-line `audited` correction in `resolution_map.json`, not yet written.
- **No full, independently-verified audit of successful merges exists yet.** After a complete skill + ingest run, 295 of 5,046 ISO subdivisions remain unmerged (`docs/unmerged_subdivisions.md`, regenerated every ingest run); most are expected to be genuine no-counterpart cases, but some are likely pipeline/skill misses rather than true gaps, and nothing yet distinguishes the two systematically. Wikidata-covered merges are cross-validated against a second source; the rest has only been spot-checked by sampling the lowest-margin automerges. A dedicated audit skill is planned, separate from resolve-subdivisions, with a tiered, falsifiable verification process (structural parent-chain consistency as a free first-pass signal, then agent/websearch-driven checks) rather than a single accept/reject gate; not yet designed in detail.

## Change history

### 2026-10-01

- Reordered this document to match the pipeline's actual execution order (alias enrichment → ISO loading/admin-level classification → skill/Wikidata precedence → automerge gates), and swapped type-family disqualification and name normalization, and ambiguity detection and best-score assignment, to match the order each actually runs in. Corrected `geonames_code`'s description (not a FIPS code).
- Fixed a bucketing bug where ISO entries at admin_level 2 and 3+ competed in separate buckets even though both draw from GeoNames' same (capped at 2) level, making any 3rd-generation entry permanently unmatchable; they now bucket together. resolve-subdivisions skill rewired to reuse the pipeline's own `candidate_pool()`/`score_candidates()` instead of a separately-maintained ranking, fixing two real gaps found in the process: missing alternate-name enrichment, and already-claimed GeoNames targets not being excluded from its candidate pool (the skill's own GeoNames map never replayed recorded resolutions onto itself). `ambiguity` orphans now carry their specific contested GeoNames targets (`AmbiguousOrphan`) instead of a bare iso_code list. Added Estonian `vald`/`linn` to the type-family token sets. After a full skill + ingest run: 295 of 5,046 ISO subdivisions remain unmerged, published at `docs/unmerged_subdivisions.md`.
- `admin_level` for ISO-sourced entries is now a recursive walk of the full parent chain instead of a one-level-deep check capped at 2, resolving France's 3-generation chain (Parsing ISO subdivisions) without a special case.
- Confirmed and added Ireland, Iceland, and Lithuania to `NON_ADMINISTRATIVE_TYPES`. Philippines ruled out on closer inspection, its regions have real administrative function (Regional Development Councils, national agency field operations), the same shape as the already-excluded Guinea-Bissau/Iraq cases, not a documentation label like the confirmed six. Malawi confirmed and added after direct research turned up an explicit statement that its regions have no administrative function and exist only to group districts.
- Added the Wikidata crosswalk as a resolution source ahead of automerge (Wikidata), cutting automerge's workload by roughly 90% and orphans by 60% in one run. Cross-validating it against the existing pipeline surfaced the populated-place-vs-admin-boundary GeoNames id pattern (142 of 144 disagreements) and left exactly one genuine open discrepancy, `RU-AL`/`RU-ALT`, now corroborated independently four times.

### 2026-09-30

- `resolution_map.json` redesigned into the single source of truth for every subdivision's resolution, with self-reconciling `audited` records (The Merge Pipeline); removed the single-token threshold discount after it produced a cluster of confirmed false positives (Fuzzy match scoring). Two further confirmed false positives found auditing the post-change cusp (`TW-TNN` Tainan/Taiwan, a GeoNames data-currency issue unrelated to thresholds; `MG-D` Antsiranana/Atsinanana, two genuinely different Madagascar divisions) are pending a correcting audit patch, not yet applied (see Known limitations).
- Initial methodology documented, covering the alt-name enrichment pipeline, the `token_set_ratio` → `token_sort_ratio` switch, the ambiguity threshold, the city/area type-family disqualification (and the reverted finer-grained version), bracket/parenthetical name splitting, and the admin_level=0 non-administrative exception mechanism (Indonesia, Dominican Republic, Cabo Verde confirmed; Ireland/Iceland/Lithuania flagged pending; Philippines/Malawi/France's 3-generation case left open).
