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

### Design

1. **Shared fetch module** — `data/fetch.py`: a `download(url: str, dest: Path)` helper on stdlib `urllib.request` (no new dependency), plus one wrapper per pipeline (`fetch_countries_sources()`, `fetch_subdivisions_sources()`, `fetch_cities_sources()`) that creates the relevant `src/` dir and downloads each file to the exact path its existing loader already expects. Skippable via an env var (e.g. `LOCALIS_SKIP_FETCH=1`) so local dev keeps working against manually-placed files without a network round-trip every run.
2. **Wire fetch into each entrypoint** — [data/countries/__main__.py](../data/countries/__main__.py), [data/subdivisions/__main__.py](../data/subdivisions/__main__.py), [data/cities/__main__.py](../data/cities/__main__.py) call their fetch wrapper first, unless skipped.
3. **Non-interactive subdivision resolution** — `resolve_unmatched_subs()` in [data/subdivisions/scripts/resolve.py](../data/subdivisions/scripts/resolve.py) gets a `non_interactive` mode (CLI flag or env var, threaded from `__main__.py`). Entries already in `resolution_map.json` auto-apply exactly as today. Entries not yet resolved are skipped (excluded from this run's dump, not prompted) and collected into a report the CI workflow surfaces in the PR body. Interactive local usage is unchanged.
4. **Provenance manifest** — after each pipeline run, write a small manifest (source URLs + fetch date) alongside the TSVs in each `src/localis/data/<dataset>/` dir. Ships with the package (check `MANIFEST.in`/build includes cover it). Add a small runtime accessor so consumers can check data vintage programmatically, and mention it in the README.
5. **New scheduled workflow** — `.github/workflows/data-refresh.yaml`: `schedule` (monthly) + `workflow_dispatch`, mirrors [test.yaml](../.github/workflows/test.yaml)'s Poetry setup, runs the three pipelines in order, then opens a PR into `dev` (not a direct commit) with any changed TSVs/manifests/`resolution_map.json`, embedding the unresolved-subdivisions report from step 3 when non-empty. Never commits the fetched raw source files themselves.
6. **`.gitignore` + tracked-file cleanup** — ignore the six files/dirs listed above for removal, with explicit exceptions for `wiki_countries.json` and `resolution_map.json`; `git rm --cached` the ones currently tracked.

### Fetch endpoints — status

- **Countries (ISO 3166-1) — confirmed.** `https://salsa.debian.org/iso-codes-team/iso-codes/-/raw/main/data/iso_3166-1.json` (Debian's `iso-codes` project). Field-for-field match with the current committed `iso3166-1.json` (`alpha_2`, `alpha_3`, `flag`, `name`, `numeric`, `official_name`), confirmed against live sample values (US/Aruba/Afghanistan matched exactly). No code changes needed beyond pointing the fetch at this URL.
- **GeoNames (countries' `geonames_countries.txt`, subdivisions' `admin1CodesASCII.txt`/`admin2Codes.txt`, cities' `allCountries.txt`) — confirmed.** Base `https://download.geonames.org/export/dump/`, already referenced in-repo. Local files are unmodified raw exports. Note: GeoNames' real filename is `admin2Codes.txt` (per README); the fetch step must save it locally as `admin2.txt` to match what the existing loader expects.
- **Subdivisions (ISO 3166-2) — blocked on a product decision, not a sourcing gap.** `iso-codes`' `data/iso_3166-2.json` (`code`/`name`/`type`/`parent`) is a viable, well-maintained source, but it has no equivalent to our `localVariant` field. [data/subdivisions/scripts/iso.py:18-28](data/subdivisions/scripts/iso.py#L18-L28) currently uses `localVariant`, when present, as the subdivision's canonical `name` (ISO name demoted to an alias) — an opinionated choice made when the data was first hand-assembled. **Decision deferred by the user**: whether local-language names should stay primary is being reconsidered as a broader "what makes this package adoptable" question, separate from the sourcing question. Do not implement the subdivisions fetch/parsing swap until this is resolved. (Housekeeping note found along the way, not urgent: `language_code`, which the current CSV has, is read by `iso.py` but never actually used — dead field regardless of source chosen.)

### Open risks to resolve during implementation

- GeoNames may rate-limit or expect a user-agent header on scripted/automated downloads of `allCountries.txt` — worth a real check before relying on it in a recurring job.
- Confirm `ubuntu-latest` runner disk comfortably fits the 1.64GB download plus parsed output (should be fine, but verify with a real run).

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
