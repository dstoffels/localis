# Data Methodology

This document describes how every record `localis` ships is produced: which sources each dataset comes from, the rules that combine them, how the results were validated, and where they are known to be wrong. It is meant to be falsifiable. Anyone who finds a result they don't trust should be able to trace it to the rule that produced it here. The rules and evidence come first; how each rule was arrived at, including the failures that motivated it, is recorded separately in the change history at the end.

## At a glance

| Dataset | Records | Sources |
|---|---|---|
| Countries | 281 (250 current, 31 historic) | ISO 3166-1, ISO 3166-3, GeoNames `countryInfo.txt`, Wikidata aliases |
| Subdivisions | 51,803 | ISO 3166-2, GeoNames `admin1CodesASCII.txt`/`admin2Codes.txt`, Wikidata crosswalk, GeoNames alternate names, Ipregistry |
| Cities | 235,914 | GeoNames `cities500.txt` |

How the 5,046 ISO 3166-2 subdivisions were resolved against GeoNames:

| Resolution | Count |
|---|---|
| Wikidata crosswalk | 3,861 |
| resolve-subdivisions skill, merged | 584 |
| Automerge | 306 |
| resolve-subdivisions skill, confirmed no GeoNames counterpart | 251 |
| Non-administrative grouping, bypassed by rule | 44 |
| **Total** | **5,046** |

4,751 ISO subdivisions (94.2%) are merged with a GeoNames counterpart. The other 295 ship as ISO-only records, and the remaining 51,508 GeoNames subdivisions make up the rest of the 51,803.

Validation and known errors:

| Check | Result |
|---|---|
| Wikidata crosswalk vs. the pipeline's own decisions, overlapping codes | 4,134 of 4,147 agree (99.7%) |
| Random sample of codes only Wikidata could resolve | 25 of 25 correct |
| resolve-subdivisions skill vs. Wikidata | 701 of 702 agree (99.9%) |
| Wikidata disagreements explained by a known GeoNames pattern | 142 of 144 |
| Confirmed wrong merges currently shipping | 2 (`MG-D`, `TW-TNN`) |
| Disputed merges | 1 pair (`RU-AL`/`RU-ALT`) |
| Records independently audited | 0 |

## Sources and licensing

`localis`'s code is MIT licensed. The data it ships is derived from the sources below and remains subject to their terms.

ISO 3166-1, 3166-2 and 3166-3 data comes from Debian's [iso-codes](https://salsa.debian.org/iso-codes-team/iso-codes) project, licensed LGPL-2.1-or-later. [GeoNames](https://www.geonames.org/) supplies `countryInfo.txt`, `admin1CodesASCII.txt`, `admin2Codes.txt`, `alternateNamesV2.txt` and `cities500.txt`, licensed CC BY 4.0, which requires attribution. [Wikidata](https://www.wikidata.org/) supplies the subdivision crosswalk and country aliases under CC0. [Unicode CLDR](https://cldr.unicode.org/) supplies `territoryInfo.json`, used only to choose which alternate-name languages to keep, under the Unicode License v3. [Ipregistry's iso3166](https://github.com/ipregistry/iso3166) repository supplies subdivision `localVariant` aliases under CC BY-SA 4.0.

The monthly ingest re-fetches a source only when its ETag changes, and the ETag of every source file behind the shipped data is recorded in `ingest/<domain>/inputs/*.manifest.json`, committed alongside the data. The commit a release was built from therefore identifies its exact source snapshot. The one exception is the Wikidata country alias list, a static snapshot stored in the repository (last updated 2026-09-30) that the monthly ingest does not refresh.

## Countries

ISO 3166-1 is the base for all 249 current ISO countries, and its codes (`alpha2`, `alpha3`, `numeric`) are never altered. A country's `name` is ISO's `common_name` where it has one, otherwise its `name`, except for a small set of deliberate overrides where ISO's short name isn't the one in common use: Republic of the Congo (CG), Democratic Republic of the Congo (CD), Falkland Islands (FK), Micronesia (FM), Saint-Martin (MF), Sint Maarten (SX), Palestine (PS), Saint Helena (SH), Holy See (VA), British Virgin Islands (VG), U.S. Virgin Islands (VI), and Vietnam (VN). `official_name` is likewise ISO's, overridden for Falkland Islands (Malvinas) (FK), Republic of Korea (KR), Lao People's Democratic Republic (LA), Collectivity of Saint Martin (MF), Country of Sint Maarten (SX), Saint Helena, Ascension and Tristan da Cunha (SH), Syrian Arab Republic (SY), Republic of China (TW), and Vatican City State (VA). A curated alias list adds well-established alternate names such as UK and Great Britain, Burma, Ivory Coast, Swaziland, and Zaire. These overrides are editorial choices, listed here in full so none of them are hidden.

The 31 ISO 3166-3 withdrawn countries, such as Czechoslovakia, Serbia and Montenegro, and Southern Rhodesia, are loaded with a `historic` record holding their four-letter `alpha_4` withdrawal code, withdrawal date, and ISO's comment. ISO has reused codes across different withdrawn countries over time: `CS` meant Czechoslovakia and later Serbia and Montenegro, numeric 891 belongs to both Yugoslavia and Serbia and Montenegro, and numeric 716 belongs to both Zimbabwe and Southern Rhodesia. A historic entry is therefore resolvable by `lookup()` only through its unique `alpha_4`, never its bare alpha2, alpha3 or numeric code, and historic entries are excluded from `filter()`, `search()` and iteration unless `include_historic` is set.

GeoNames' `countryInfo.txt` is matched to ISO entries by alpha2, and to historic entries by their former alpha2. It contributes each country's `geonames_id`, plus its GeoNames name as an alias when that name differs from the ISO names. ISO stays authoritative for the name itself. A GeoNames country with no ISO 3166-1 or 3166-3 counterpart is added as a country in its own right; the only such entry is Kosovo (`XK`), which has no ISO assignment.

Wikidata aliases are added last. An alias is kept only if it is longer than three characters, doesn't contain "ISO 3166", and doesn't duplicate the country's codes, name or official name.

## Subdivisions

ISO 3166-2 is the authority for a subdivision's official name, type and administrative hierarchy. GeoNames is the authority for its stable numeric `geonames_id`, its `geonames_code` (GeoNames' own admin code string such as `US.CA`, not a FIPS code), and a large corpus of alternate names. Where the two disagree, ISO's structure wins and GeoNames supplies enrichment.

### GeoNames subdivisions

The 51,508 entries in `admin1CodesASCII.txt` and `admin2Codes.txt` are parsed first. Each takes its country from its `geonames_code` and its `admin_level` from the file it came from; a merged ISO counterpart's level replaces it downstream.

Aliases come from GeoNames' `alternateNamesV2.txt`, filtered to English plus the official language or languages of the subdivision's country according to CLDR. Names flagged historic or colloquial, non-name entries such as links and postal codes, and duplicates are excluded, and invisible bidirectional control characters are stripped. Enrichment happens before matching, so the extra name variants also take part in fuzzy comparison. Ipregistry's `localVariant` names are added to ISO subdivisions as aliases.

### ISO subdivisions

Some ISO names carry trailing bracketed or parenthetical content, which is one of three things: a genuine alternate name (`"Girona [Gerona]"`), a bare subdivision code (`"Stockholms län [SE-01]"`), or a territory-dispute or type annotation (`"Aousserd (EH)"`, `"Amānat al 'Āşimah [city]"`). The content is split off at load time. A genuine alternate name becomes an alias and everything else is discarded, so it never pollutes matching.

`admin_level` is computed from ISO's own parent chain: 1 plus the number of administrative ancestors above the entry. Nothing caps the depth. The current data spans levels 0 to 3, where 1 is a top-level division, 2 a second-level division such as a county or district, 3 the deepest nesting observed so far (France's régions, collectivités and départements), and 0 a non-administrative grouping.

A grouping is non-administrative only if it passes two tests: structurally it exists only to group real divisions, and it has no administrative function at all, verified independently. Seven countries currently qualify. Indonesia groups its 38 provinces under 7 "Geographical unit" entries. The Dominican Republic groups its 31 provinces and the Distrito Nacional under 10 planning "Region" entries. Cabo Verde groups its 22 municipalities under two "Geographical region" island groups. Ireland groups its 26 counties under 4 ceremonial "Province" entries. Iceland groups its 64 municipalities under 8 statistical "Region" entries. Lithuania groups its 60 municipalities under 10 "County" entries that have had no governing authority since 2010. Malawi groups its 28 districts under 3 statistical "Region" entries. Groupings that look structurally identical but have real administrative function do not qualify: Guinea-Bissau's provinces, Iraq's Kurdistan Region, and the Philippines' regions, which have Regional Development Councils and national agency field operations, are all treated as real levels.

The rule is stored by country and type in `NON_ADMINISTRATIVE_TYPES` in `ingest/subdivisions/outputs/resolution_map.json`, so it covers new matching entries automatically. A matching entry gets `admin_level=0`, keeps its real ISO `parent` reference, and bypasses GeoNames matching entirely, since GeoNames' admin files never represent such groupings as places. Its children compute their own levels as if it weren't there.

### Merge precedence

`resolution_map.json` is the single record of how every ISO subdivision was resolved. Resolutions apply in a fixed order: resolve-subdivisions skill decisions first, then the Wikidata crosswalk, then automerge for whatever remains. An earlier stage's decision can never lose its GeoNames target to a later one, because the later stage never sees that subdivision.

Any ISO subdivision still unresolved after automerge is an orphan, sorted into one of three buckets: `ambiguity` (several close GeoNames candidates), `no_candidates` (none at all), and `no_matches` (candidates exist but none qualifies). If any orphan remains, ingest exits with code 10 before writing any data, so the shipped dataset never contains an unresolved subdivision. Orphans are resolved with the resolve-subdivisions skill.

Wikidata and automerge results are recomputed on every run. A separate `audited` record is meant to hold independently verified decisions. Each run compares fresh results against it, keeps an audited entry only while the fresh result agrees, and evicts it otherwise so it is reviewed again. `audited` confirms results; it cannot override them, so a correction has to go through a skill decision. No subdivision has been independently audited yet, and `audited` is currently empty.

### The resolve-subdivisions skill

The resolve-subdivisions skill is an AI agent, run through Claude Code, that resolves orphans. It works under fixed constraints. It can only choose a GeoNames candidate supplied by the pipeline's own candidate pool, filtered by the same type and direction rules automerge uses, and it can never invent an ID. It must run a web search before declaring that an orphan has no GeoNames counterpart. When it is not confident, it escalates the orphan to a human, who decides to merge it or add it as-is. Every outcome is written to `skill_resolved` and stays permanent until a human revisits it; the record holds the outcome, not whether the agent or a human made the decision.

The candidates shown depend on the orphan's bucket. An `ambiguity` orphan sees its specific contested candidates first, then the normal pool for its country and level. A `no_candidates` orphan sees every GeoNames subdivision in its country, regardless of level. A `no_matches` orphan sees batches of fuzzy-sorted candidates. Cross-checked against Wikidata, the skill's merges agree 701 of 702 times.

### Wikidata crosswalk

Wikidata is queried for every item carrying both an ISO 3166-2 code (P300) and a GeoNames ID (P1566), keeping only codes that map to exactly one GeoNames ID; 4,322 codes qualify. A match is applied only if that ID exists in localis's GeoNames admin data and belongs to the same country as the ISO code. Anything else falls through to automerge.

Most remaining disagreements with the rest of the pipeline come from one GeoNames pattern: a place often has two GeoNames records, an administrative-boundary record (the kind in `admin1CodesASCII.txt` and `admin2Codes.txt`) and a populated-place record, and Wikidata's P1566 sometimes points at the populated-place one. Such an ID doesn't exist in localis's admin data, so the validation above already rejects it. That pattern accounts for 142 of the 144 disagreements, and it holds for every Hungarian city with county rights and every Marshall Islands municipality.

### Automerge

Automerge compares each remaining ISO subdivision only with unclaimed GeoNames subdivisions of the same country and administrative level. Level 3 is grouped with level 2, since GeoNames never nests deeper than 2. A pair must clear every gate below, in order.

#### 1. Type-family disqualification

A pair is rejected before scoring if GeoNames' raw, unstripped name or aliases carry a qualifier word from a different family than the ISO side's `type`. There are deliberately only two families: `city` (city, shi, si, gorodskoy, town, and equivalents) and `area` (everything else). This stops a city from taking its surrounding region's record on string similarity alone. `UA-30` Kyiv, the city, otherwise matches GeoNames' `UA.13`, which is Kyiv Oblast. Finer families such as province against county are not used, because sources describe the same tier with different translated words.

#### 2. Name normalization and noise-token stripping

Both sides' names and aliases are lowercased, diacritics-normalized, and stripped of administrative qualifier words (`NOISE_TOKENS`), so "Province" on one side and nothing on the other doesn't cost a match. The token list spans dozens of languages and was built by counting the recurring leading and trailing words in GeoNames' raw admin names.

#### 3. Fuzzy match scoring

Pairs are scored with `token_sort_ratio` against a threshold of 90, lowered by 15 for names averaging five characters or fewer, by 10 for eight or fewer, and by 5 for twelve or fewer, since a single edit matters more in a short name. `token_sort_ratio` is used instead of `token_set_ratio` because the latter rates a full token subset as a near-perfect match, which is wrong when the extra words name a different place: "Val-de-Marne" is not "Marne". A separate check vetoes any pair that differs only by a directional word such as north, south, east, west, upper, lower or central. Where a false merge and an unmerged record trade off, the threshold favors leaving the record unmerged, since a false merge ships silently as fact while an unmerged record is visible and recoverable.

#### 4. Ambiguity threshold

Before any assignment, a GeoNames target that two or more different ISO subdivisions each score 90 or higher against is excluded from automerge. This catches namesake collisions, most often a city and its surrounding district sharing a bare name, where string similarity cannot break the tie. Those ISO subdivisions become `ambiguity` orphans.

#### 5. Global best-score assignment

Remaining pairs are claimed in descending score order across the whole bucket, so a strong match is never blocked by a weaker one claimed earlier in iteration.

## Cities

Cities come from GeoNames' `cities500.txt`, GeoNames' own export of every populated place with a population of 500 or more, plus administrative seats of any size. No further population or feature filtering is applied. A city without a country code, or whose country isn't in localis's country data, is dropped and logged. A missing population is recorded as 0.

A city's country is attached by its ISO alpha2 code. Its subdivisions are attached through its GeoNames admin1 and admin2 codes: the deepest one that resolves is taken, and its parent chain is walked to the top, so `City.subdivisions` holds the city's full administrative chain in ascending `admin_level` order. That includes ISO levels GeoNames itself doesn't have, such as France's third level or a non-administrative grouping. A city can only link to a subdivision that has a GeoNames code, so the 295 ISO-only subdivisions never appear directly as a city's subdivision. A city's `name` is GeoNames' primary name; alternate city names are not shipped.

## Known limitations

Two automerged subdivisions are confirmed wrong and still ship. `MG-D` (Antsiranana) merged with Atsinanana, a different Madagascar division with a similar name, at a margin of 1 over the threshold. `TW-TNN` (Tainan) merged with a GeoNames record from Taiwan's outdated four-province structure instead of the modern entry, at a margin of 3. Correcting either requires a `skill_resolved` decision, since `audited` cannot override an automerge result.

`RU-AL` and `RU-ALT` (Altai Republic and Altai Krai, two real, easily confused Russian federal subjects) are disputed. Wikidata and the pipeline assign the same two valid GeoNames IDs the opposite way round, and since both sources are internally consistent, settling it needs direct research rather than another automated check.

The 295 unmerged ISO subdivisions, listed in [unmerged_subdivisions.md](unmerged_subdivisions.md) and regenerated on every ingest, are expected to be mostly genuine no-counterpart cases. Some are likely missed matches, though, and each miss means a place may appear twice in the dataset, once as its ISO record and once as its GeoNames record.

No independent audit of successful merges exists. Wikidata-resolved merges are cross-validated against a second source, and the rest have been spot-checked by sampling the lowest-margin automerges. A dedicated audit process is planned but not yet designed.

The Wikidata country aliases are a static snapshot and aren't refreshed by the monthly ingest.

## Change history

### 2026-10-02

Restructured this document to cover all three datasets, not just subdivisions, and to separate the rules and evidence from the history of how they were reached. Added summary tables, source licensing, source snapshot provenance, country and city methodology, and the constraints on the resolve-subdivisions skill. Corrected an earlier claim that `MG-D` and `TW-TNN` could be fixed with an `audited` entry. `audited` only confirms results and evicts entries that disagree, so the fix has to be a `skill_resolved` decision.

### 2026-10-01

ISO entries at levels 2 and 3 previously competed in separate automerge buckets, even though both draw on GeoNames' level-2 data, which left every third-level entry unmatchable. They now share a bucket. The skill was rewired to use the pipeline's own `candidate_pool()` and `score_candidates()` instead of a separately maintained ranking, which fixed two gaps found in the process: its candidates lacked alternate-name enrichment, and GeoNames targets already claimed by recorded resolutions still appeared as candidates. `ambiguity` orphans now carry their contested GeoNames targets. Estonian `vald` and `linn` were added to the type-family word lists, since GeoNames' Estonian names append them.

`admin_level` became a recursive walk of ISO's full parent chain instead of a one-level check capped at 2, resolving France's third level without a special case. Ireland, Iceland, Lithuania and Malawi were added to the non-administrative rule, Malawi after research found an explicit statement that its regions exist only to group districts. The Philippines was ruled out on closer inspection, because its regions have real administrative function.

The Wikidata crosswalk was added ahead of automerge and resolved roughly 3,861 subdivisions in its first run, cutting automerge's workload by about 90% and orphans by about 60%. Before it went live, every match was checked against the pipeline's existing decisions (4,134 of 4,147 agreed), and a random sample of 25 resolutions only Wikidata could make came back 25 of 25 correct. Checking all 144 disagreements surfaced the populated-place pattern behind 142 of them. The remaining dispute, `RU-AL`/`RU-ALT`, had already surfaced independently in three earlier checks: the type-family disqualification work, the lowest-margin audit, and an earlier crosswalk comparison.

After a full skill and ingest run, 295 of 5,046 ISO subdivisions remained unmerged. The list is published in `unmerged_subdivisions.md` and regenerated on every ingest.

### 2026-09-30

`resolution_map.json` was redesigned into the single record of every subdivision's resolution, with self-reconciling `audited` entries.

Fuzzy scoring previously gave single-token names an extra 5-point discount on top of the length discount. Auditing the lowest-margin merges found confirmed false positives sitting exactly on the resulting threshold: `GB-ENF` Enfield matched Wakefield at exactly 75 against a threshold of exactly 75, two unrelated places sharing only a "-field" suffix, and `GB-EAL` Ealing/Reading, `PL-16` Opolskie/Podlasie, `VN-31` and `VN-32` showed the same knife-edge pattern. Removing the discount pushed about 16 correct transliteration and grammatical-variant matches (Panjshayr/Panjshir, Kordestān/Kurdistan, several Russian oblasts' case endings) into orphan status in exchange for closing 5 to 7 confirmed false positives. The trade was taken deliberately. Auditing the new lowest-margin merges then found `TW-TNN` and `MG-D`, both still uncorrected.

Type-family disqualification was introduced after `UA-30` Kyiv, the city, automerged with Kyiv Oblast's GeoNames record on a near-perfect bare-name score, while `UA-32`, the actual oblast, never scored well enough to compete. Vilnius (`LT-58`) and Altai showed the same pattern. A finer-grained version with separate province, department, county and region families was tried first and reverted, after it wrongly rejected nearly every Romanian and Swedish match: GeoNames names Romanian counties "Vâlcea County" while ISO types them "Department", and Sweden's "län" landed in the wrong family. Collapsing to city against area removed 150 wrongly orphaned entries.

`token_sort_ratio` replaced `token_set_ratio` after subset matches merged different places, and ISO names with trailing bracketed content are now split at load time, after `"Stockholms län [SE-01]"` normalized three junk tokens away from GeoNames' "Stockholms".

Initial methodology documented, covering alternate-name enrichment, the scorer change, the ambiguity threshold, type-family disqualification, bracket splitting, and the non-administrative exception for Indonesia, the Dominican Republic and Cabo Verde.
