# Project Plan
## Overview

This document outlines the project plan for the Localis project, detailing the objectives, scope, timeline, and key milestones.

## Objectives

- Bring API, data merging/validation and automated data fetching to release v1.0

## MVP Features

~~- Update cities registry to lazy load for faster initialization/import.~~
~~- Implement resolve-subdivisions skill & MCP for locally automated data reconciliation when merging ISO and geonames datasets.~~
~~- Add checksums to data fetching to skip unnecessary downloads~~
- Implement cron job in GHA ci for automated data fetching, updating the dataset and drafting a PR if the merging of the new data succeeds. If it cannot be merged automatically, notify the team for manual intervention.


## Backlog
- Implement autocomplete for registries and/or global interface.
- Patch missing flags for countries
- Implement native languages in countries?

## Ingest CI cron job (implementation plan)

### Context

The last MVP item is a scheduled CI job that fetches upstream data, merges it, and drafts a PR when it succeeds, or signals for manual intervention when it can't fully resolve (unmerged subdivisions). The checksum-aware fetching and ingest-side gating already built are the prerequisites this depends on: they're what make "did anything actually change" a trustworthy signal instead of noise.

The architecture: `ingest` is a long-lived branch (already exists locally and on `origin`) that CI runs against on a monthly schedule and on every push to it. CI commits whatever the ingest pipeline produces straight back to `ingest`, and maintains a single PR from `ingest` into `main`. When subdivisions can't be fully auto-resolved, the run still commits and pushes whatever did resolve, including the freshly-written `orphaned_subdivisions.json`, so the PR reflects real partial progress, then fails at the end (GitHub already emails repo owners on scheduled-workflow failures, so no extra notification plumbing is needed). The maintainer pulls `ingest`, runs the resolve-subdivisions skill locally, commits, and pushes back to `origin/ingest`, which re-triggers the same workflow via the push trigger.

This originally required a behavior change: `resolve_subdivisions.py`'s `handle_orphans()` used to call `sys.exit(10)` the moment it found any orphan, before `ingest_subdivisions()` ever reached `sub_map.refresh()`/`dump(sub_map)`, so a run with orphans wrote nothing at all, which would've defeated "commit whatever succeeded." That call has been removed (the function is now `dump_orphans()` and only writes `orphaned_subdivisions.json`), so the pipeline always runs to completion and dumps whatever it resolved regardless of leftover orphans. The exit-code signal isn't needed either: CI can just check `orphaned_subdivisions.json`'s content directly after the run, since that file is the actual source of truth and it's already committed to the branch.

### Code change: stop losing partial progress on orphans

Done. `resolve_subdivisions.py`'s `dump_orphans()` (formerly `handle_orphans()`) no longer calls `sys.exit()`; it only writes the file. `ingest_countries()` and `ingest_cities()` needed no changes; their gating was already ordered correctly.

### New workflow: `.github/workflows/ingest.yaml`

Triggers: `schedule` (monthly cron) and `push: branches: [ingest]`.

Job steps, following `test.yaml`'s existing conventions (`ubuntu-latest`, `actions/checkout@v4`, `actions/setup-python@v5` at `3.11`, `snok/install-poetry@v1`, `actions/cache@v3` keyed on `poetry.lock`):

1. Checkout with `ref: ingest` explicitly (the schedule trigger doesn't default to it).
2. Install Python/Poetry deps (mirrors `test.yaml`).
3. Configure git identity (`github-actions[bot]` / `github-actions[bot]@users.noreply.github.com`).
4. Run `poetry run ingest` (always exits 0 now).
5. `git add -A` (raw dir is gitignored except the manifest/resolution files already whitelisted, so this only ever picks up `src/localis/data/**` plus those state files) then check `git diff --cached --quiet` to decide whether there's anything to commit at all. If nothing changed, the job ends here, successfully, no commit/PR/failure.
6. If there is a diff: commit and `git push origin ingest`.
7. Ensure a PR exists: `gh pr list --head ingest --base main --json number` to check, `gh pr create --draft --head ingest --base main --title ... --body ...` if none exists yet. No explicit "update" step needed; GitHub reflects new commits on `ingest` into the existing PR's diff automatically.
8. Check `data/subdivisions/raw/orphaned_subdivisions.json` directly (a small `python -c` one-liner: exit 1 if it parses to a non-empty object, 0 otherwise) to decide the orphan state, rather than relying on any exit code from step 4.
9. If that check found no orphans and the PR is currently a draft: `gh pr ready`.
10. If that check found orphans: fail the job now, after steps 5-9 have already run.

Needs `permissions: contents: write` and `pull-requests: write` on the job (default `GITHUB_TOKEN` covers both; no PAT needed since PR target and source are the same repo).

### Verification

- Unit-level: run `poetry run ingest` locally against a manually-seeded orphan (or temporarily force one) and confirm `subdivisions.tsv`/its indexes are written and `orphaned_subdivisions.json` is populated, with the process still exiting `0`.
- Workflow-level: push a trivial change to `origin/ingest` and watch the Actions run: confirm it checks out `ingest`, runs ingest, and either short-circuits cleanly (no upstream changes) or commits and opens/updates the draft PR against `main`.
- Confirm `gh pr list --head ingest --base main` shows at most one PR after repeated runs (idempotency), and that it flips out of draft only on a run that both changed data and left no orphans.