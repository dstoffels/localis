# localis `dev` branch: data provenance + eager/lazy loading — Part 1 scoped

## Context

This updates the plan previously tracked in this file. Part 1: Data Provenance was "Not started"; Part 2: Eager/Lazy Loading for Cities was "Mostly done." This update turns Part 1 from a goal statement into a concrete, narrowed design based on a full scan of `data/`. Part 2 is untouched by this update and is carried forward below exactly as it stood, for continuity only.

## Part 1: Data Provenance — scoped design

Goal (unchanged): stop treating raw upstream dumps as repo state — fetch them at run time instead — and automate the rebuild via scheduled CI that opens a PR rather than auto-publishing, gating any new subdivision-mapping ambiguity on a human.

### What the scan found

Three sequential pipelines, each a `python -m data.<name>` entrypoint, run in strict order because each stage reads the previous stage's freshly-dumped **live** TSVs (`src/localis/data/<name>/`, via `data/utils.py`'s `load_countries()`/`load_subdivisions()`):

- **countries** ([data/countries/__main__.py](../data/countries/__main__.py)): `init_iso_countries()` reads `data/countries/src/iso3166-1.json` (Ipregistry) → `merge_wikidata()` reads `data/countries/src/wiki_countries.json` → `merge_geonames()` reads `data/countries/src/geonames_countries.txt` (GeoNames `countryInfo.txt`) → dumps 4 TSVs.
- **subdivisions** ([data/subdivisions/__main__.py](../data/subdivisions/__main__.py)): reads `admin1CodesASCII.txt`/`admin2.txt` (GeoNames) and `iso-3166-2.csv` (Ipregistry) → fuzzy-matches → **`resolve_unmatched_subs()`** in [data/subdivisions/scripts/resolve.py](../data/subdivisions/scripts/resolve.py) blocks on an interactive terminal wizard for anything unmatched, persisting decisions into `data/subdivisions/src/resolution_map.json` (678 entries today, 0 unresolved for the current snapshot) → dumps 4 TSVs.
- **cities** ([data/cities/__main__.py](../data/cities/__main__.py)): reads `data/cities/src/allCountries.txt` (GeoNames, 1.64GB — this directory doesn't exist in the repo yet; the file is already gitignored and has always been hand-downloaded per the script's own header comment) → dumps 4 TSVs.

**Stop committing, fetch at run time instead (same local paths, no downstream code changes needed):**
`data/countries/src/geonames_countries.txt`, `data/countries/src/iso3166-1.json`, `data/subdivisions/src/admin1CodesASCII.txt`, `data/subdivisions/src/admin2.txt`, `data/subdivisions/src/iso-3166-2.csv`, and `data/cities/src/allCountries.txt` (new dir, created at run time).

**Stay committed — narrower than the original "everything except allCountries.txt moves" framing:**
- `data/countries/src/wiki_countries.json` — confirmed still genuinely used by `merge_wikidata()` (not dead code), but has no fetch script or documented source URL anywhere in the repo. No reproducible way to automate it exists today, so it stays a static seed file, read as-is.
- `data/subdivisions/src/resolution_map.json` — not raw source data; it's the persistent record of human subdivision-mapping decisions. Gets *updated* by the process, never fetched or regenerated.

**Already resolved, drop from scope:** the stale `pyproject.toml` → `localis = 'localis.cli:main'` entry point (`src/localis/cli.py` doesn't exist) is gone — confirmed by reading the current `pyproject.toml`, which only declares `test`/`test-watch` scripts. This matches git log commit `332b1fa fix: remove dead CLI path`. No action needed here.

### Hand-curated mapping audit — completed

Before automating ingestion, the manual override maps baked into the pipeline (undocumented editorial decisions made when the data was first hand-assembled) were audited for accuracy and consistency. Fixes already applied:

- [data/countries/scripts/load.py](../data/countries/scripts/load.py) `ALIAS_MAP`: fixed a typo ("Carribean Netherlands" → "Caribbean Netherlands"); flipped `VN` so `NAME_MAP["VN"] = "Vietnam"` (the common current form) is primary and `"Viet Nam"` (the formal ISO form) is the alias, reversing what was backwards relative to every other entry in that map; removed `GB`'s `England`/`Scotland`/`Wales`/`Northern Ireland` aliases (these are constituent countries and real subdivisions of the UK, not alternate names for it — aliasing them at the country level risked colliding with the actual subdivision entities); removed `RU`'s `USSR`/`Soviet Union` and `RS`'s `Yugoslavia` aliases (unlike a same-country rename like Zaire→DRC or Burma→Myanmar, these predecessor states dissolved into many present-day countries, so a 1:1 alias to one successor state implies a false equivalence). `RU`'s plain `"Russia"` alias was kept — that one's just the common name vs. the formal "Russian Federation," same category as `US`→"America".
- [data/subdivisions/scripts/iso.py](../data/subdivisions/scripts/iso.py): confirmed with a real example (Bangladesh's `BD-B`/`BD-10`, "Chattogram" vs. the old colonial name "Chittagong") that `localVariant` can't be trusted as the more "contemporary" name — sometimes it's a genuine local-language form, sometimes it's just an outdated one, and the ISO `name` field isn't consistently which. Fixed so `name` is always the ISO reference name (never conditionally overridden), and `local_variant` is unconditionally demoted to an alias when present (same rationale as keeping "Burma"/"Zaire" as country aliases — still a name people search for, just not the canonical one). Also fixed a truthiness check that tested `if name` (always true) instead of `if local_variant`, which happened to not cause a functional bug due to a downstream filter, but was misleading and fragile.

**Known stale data, deliberately deferred, not fixed yet:** `data/countries/raw/wiki_countries.json` independently supplies `"USSR"` as a `RU` alias and `"Yugoslavia"` as an `RS` alias (its own `aliases` field, merged in by `merge_wikidata()`). This silently re-adds the exact two aliases removed from `load.py`'s `ALIAS_MAP` above, for the same reason they were removed — `is_valid_name()` in `merge.py` has no check that would catch them. The `ALIAS_MAP` fix is currently cosmetic for these two cases; a real fix needs to happen where the two paths converge (e.g. a shared deny-list `is_valid_name()` also checks), not just in `load.py`. Confirmed by reading the full file directly (`wiki_countries.json` line ~1237 for `RU`, ~1328 for `RS`) — not a guess. Revisiting later; not blocking anything currently in progress.

### Design

1. **Shared fetch module** — `data/fetch.py`: a `download(url: str, dest: Path)` helper on stdlib `urllib.request` (no new dependency), plus one wrapper per pipeline (`fetch_countries_sources()`, `fetch_subdivisions_sources()`, `fetch_cities_sources()`) that creates the relevant `src/` dir and downloads each file to the exact path its existing loader already expects. `fetch_cities_sources()` downloads `allCountries.zip` and unzips it to `allCountries.txt` (stdlib `zipfile`, no new dependency). Skippable via an env var (e.g. `LOCALIS_SKIP_FETCH=1`) so local dev keeps working against manually-placed files without a network round-trip every run.
2. **Wire fetch into each entrypoint** — [data/countries/__main__.py](../data/countries/__main__.py), [data/subdivisions/__main__.py](../data/subdivisions/__main__.py), [data/cities/__main__.py](../data/cities/__main__.py) call their fetch wrapper first, unless skipped.
3. **Non-interactive subdivision resolution** — `resolve_unmatched_subs()` in [data/subdivisions/scripts/resolve.py](../data/subdivisions/scripts/resolve.py) gets a `non_interactive` mode (CLI flag or env var, threaded from `__main__.py`). Entries already in `resolution_map.json` auto-apply exactly as today. Entries not yet resolved are skipped (excluded from this run's dump, not prompted) and collected into a report the CI workflow surfaces in the PR body. Interactive local usage is unchanged.
4. **Provenance manifest** — after each pipeline run, write a small manifest (source URLs + fetch date) alongside the TSVs in each `src/localis/data/<dataset>/` dir. Ships with the package (check `MANIFEST.in`/build includes cover it). Add a small runtime accessor so consumers can check data vintage programmatically, and mention it in the README.
5. **New scheduled workflow** — `.github/workflows/data-refresh.yaml`: `schedule` (monthly) + `workflow_dispatch`, mirrors [test.yaml](../.github/workflows/test.yaml)'s Poetry setup, runs the three pipelines in order, then opens a PR into `dev` (not a direct commit) with any changed TSVs/manifests/`resolution_map.json`, embedding the unresolved-subdivisions report from step 3 when non-empty. **Opens the PR as a draft whenever that report is non-empty** (see "Unresolved-subdivision handling" below); a normal, ready-for-review PR otherwise. Never commits the fetched raw source files themselves.
6. **`.gitignore` + tracked-file cleanup** — ignore the six files/dirs listed above for removal, with explicit exceptions for `wiki_countries.json` and `resolution_map.json`; `git rm --cached` the ones currently tracked.

### Unresolved-subdivision handling — decided

The ~678 entries already in `resolution_map.json` need no automation beyond what `resolve_unmatched_subs()` already does — it auto-reapplies any cached decision on every run with zero human involvement. The only open question was what happens for genuinely *new* unmatched codes (rare — new ISO 3166-2 codes don't appear often). Automating the resolution itself was ruled out: the fuzzy match (`rapidfuzz.token_set_ratio`, threshold ~90, floor 70) is already the automated pass, and anything landing in "unmatched" failed to clear that bar — loosening it further to auto-resolve more would mean accepting lower-confidence merges automatically, which risks silently corrupting a real subdivision record downstream.

So new unmatched codes are always skipped from that run's dump and reported (per step 3 above), and three merge policies were weighed:
1. Never block — flag only in the PR body. Simplest, but a note can get skimmed past and a genuinely new subdivision could stay unresolved indefinitely.
2. **Open the PR as a draft whenever the report is non-empty — chosen.** A normal, ready-for-review PR when nothing's unresolved; a draft otherwise, flipped to ready once `resolve.py` is run locally and the updated `resolution_map.json` is pushed to that same branch. Doesn't hard-block (drafts can still be force-merged), but is a real, visible speed bump against an absent-minded merge — appropriate for a single-maintainer repo with no other reviewer to catch it.
3. Hard-block via a required CI check that fails on any non-empty report. Rejected: would stall that entire month's refresh — including already-correct country/city data — behind resolving what might be one obscure subdivision, coupling unrelated data unnecessarily.

**Still to document once the pipeline is built:** the actual runbook for a maintainer handling a draft PR — running `resolve.py` locally against the same fetched source data the workflow used (not a fresh re-download that might differ), pushing the updated `resolution_map.json`, and marking the PR ready.

### Fetch endpoints — status

- **Countries (ISO 3166-1) — confirmed.** `https://salsa.debian.org/iso-codes-team/iso-codes/-/raw/main/data/iso_3166-1.json` (Debian's `iso-codes` project). Field-for-field match with the current committed `iso3166-1.json` (`alpha_2`, `alpha_3`, `flag`, `name`, `numeric`, `official_name`), confirmed against live sample values (US/Aruba/Afghanistan matched exactly). No code changes needed beyond pointing the fetch at this URL.
- **GeoNames (countries' `geonames_countries.txt`, subdivisions' `admin1CodesASCII.txt`/`admin2Codes.txt`, cities' `allCountries.txt`) — confirmed.** Base `https://download.geonames.org/export/dump/`, already referenced in-repo. Local files are unmodified raw exports. Note: GeoNames' real filename is `admin2Codes.txt` (per README); the fetch step must save it locally as `admin2.txt` to match what the existing loader expects.
  - **Cities' `allCountries.txt` — tested live, one correction to the existing repo comment.** [data/cities/__main__.py:9](../data/cities/__main__.py#L9) says to download `allCountries.txt` directly, but a live `HEAD` request confirms that path 404s — GeoNames only serves it as `allCountries.zip` (verified: 402MB compressed, vs. the 1.64GB uncompressed size the comment cites). The fetch step downloads `allCountries.zip` and unzips it to `allCountries.txt` (confirmed this unzips to the exact filename/format `load_cities()` already reads — same complete dataset, just compressed for transport, no data-scope change). No rate-limiting or user-agent blocking observed — a plain request with default `curl` got a clean `200 OK`. A smaller pre-filtered GeoNames export (`cities500.zip` etc.) was considered and rejected: those apply a population floor that [data/cities/scripts/load.py:44-53](../data/cities/scripts/load.py#L44-L53)'s `is_valid_city()` doesn't use today (it accepts population ≥ 1, no floor), so switching would silently shrink the ~451,792-city dataset.
- **Subdivisions (ISO 3166-2) — confirmed.** `https://raw.githubusercontent.com/ipregistry/iso3166/main/subdivisions.csv` — confirmed as the actual origin of the current committed `iso-3166-2.csv` (exact column match: `country_code`, `iso_code`, `name`, `language_code`, `parent_iso_code`, `category`, `localVariant`). Checked freshness directly via the GitHub API: last commit **2026-08-26**, message "Automatic update for ISO data on August 26, 2026" — the upstream project runs its own scheduled bot to keep this current, so it's actively maintained, not stale. The `localVariant`-vs-`name` precedence question is resolved (see mapping audit above): `iso.py` now always takes `name` as primary and `localVariant` as an alias, so this source's shape is exactly what the pipeline needs — no swap to a different source required. (Housekeeping note found along the way, not urgent: `language_code`, which the CSV has, is read by `iso.py` but never actually used — dead field, harmless either way.)

### Open risks — resolved

- ~~GeoNames rate-limiting/user-agent blocking~~ — tested live, confirmed a non-issue (see above).
- ~~Runner disk space for the 1.64GB download~~ — moot: only a 402MB zip transfers over the network; even with the unzipped 1.64GB `allCountries.txt` plus parsed output sitting alongside it, total footprint is comfortably under `ubuntu-latest`'s ~14GB free disk.

**Critical files:** `data/countries/__main__.py`, `data/subdivisions/__main__.py`, `data/cities/__main__.py`, `data/subdivisions/scripts/resolve.py`, `data/subdivisions/src/resolution_map.json`, `data/utils.py`, new `data/fetch.py`, `.github/workflows/data-refresh.yaml`, `.gitignore`.

## Part 2: Eager/Lazy Loading for Cities — Mostly done (carried forward, unchanged)

Done:
- `CityRegistry.LAZY_LOAD = True`; `_cache`/`_lookup_index`/`_filter_index`/`_search_index` are all `cached_property`, so every access path triggers lazy load correctly. `load_all()` renamed to `force_cache()`.
- Regression found and fixed (commit `bc3079d`): `cached_property` conversion broke `SubdivisionRegistry`'s parent-lookup (mid-build `RecursionError`), fixed by threading the in-progress cache dict explicitly through `parse_row(...)`.
- Thread-safety: resolved as a documentation note (README "Concurrency" section: call `.force_cache()` before concurrent access), not code — deemed low-risk since load/index-build is read-only/self-contained.
- Bonus, not originally in the plan: added `test`/`test-watch` console scripts to `pyproject.toml`.

Still outstanding:
- No test coverage for the lazy-load behavior itself.
- README's load-time numbers are stale and `tests/analysis/benchmarks.py` has never measured cache/index *build* time (only search speed) — needs extending to instrument `force_cache()`'s four steps individually, accounting for the fact that `localis.countries`/`subdivisions`/`cities` singletons finish eager-loading as a side effect of `import localis` itself.

## Verification

- **Part 1:** run each pipeline locally end-to-end with real fetches; confirm regenerated TSVs match today's committed ones for unchanged sources; confirm the manifest is written and packaged. Temporarily strip one entry from a scratch copy of `resolution_map.json`, rerun subdivisions in non-interactive mode, confirm it skips and reports that entry without blocking. Run `poetry run pytest` against freshly generated TSVs. Manually trigger `data-refresh.yaml` via `workflow_dispatch` once merged and confirm it opens a PR with the expected diff, without any large fetched file landing in git history.
- **Part 2 (already tracked, unchanged):** add/extend unit tests for lazy-cache behavior; implement the cache/index-build-time benchmark instrumentation; update README's Caching section with real measured numbers.
