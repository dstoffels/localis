# Project Plan
## Overview

This document outlines the project plan for the Localis project, detailing the objectives, scope, timeline, and key milestones.

## Objectives

- Bring API, data merging/validation and automated data fetching to release v1.0

## MVP Features

~~- Update cities registry to lazy load for faster initialization/import.~~
~~- Implement resolve-subdivisions skill & MCP for locally automated data reconciliation when merging ISO and geonames datasets.~~
~~- Add checksums to data fetching to skip unnecessary downloads~~
~~- Implement cron job in GHA ci for automated data fetching, updating the dataset and drafting a PR if the merging of the new data succeeds. If it cannot be merged automatically, notify the team for manual intervention.~~


## Backlog
- Implement autocomplete for registries and/or global interface.
- Patch missing flags for countries
- Implement native languages in countries?

## Ingest CI cron job

### Context

A scheduled CI job fetches upstream data, merges it, and drafts a PR when it succeeds, or blocks for manual intervention when it can't fully resolve (unmerged subdivisions). The checksum-aware fetching and ingest-side gating built earlier are the prerequisites this depends on: they're what make "did anything actually change" a trustworthy signal instead of noise.

`ingest` is a long-lived branch that CI runs against on a monthly schedule and on every push to it. CI commits whatever the ingest pipeline produces straight back to `ingest`, and maintains a single PR from `ingest` into `main`. `resolve_subdivisions.py`'s `dump_orphans()` (formerly `handle_orphans()`, which used to hard `sys.exit(10)` the moment it found any orphan, before the pipeline ever dumped anything) now just writes `orphaned_subdivisions.json` and lets the pipeline run to completion regardless, so a run with unresolved orphans still commits and pushes whatever *did* resolve. CI checks that file's content directly after the run (via `data/subdivisions/scripts/check_orphans.py`, exposed as `poetry run check-orphans`) rather than relying on any exit code, since the file is the actual source of truth and it's already committed to the branch. When it's non-empty, the script prints a markdown summary (each orphaned ISO code, name, country, and the resolve-subdivisions-skill instructions), which CI posts as a real comment on the PR, and the job fails at the end so it's visible in the Actions tab too. The maintainer pulls `ingest`, runs the resolve-subdivisions skill locally, commits, and pushes back to `origin/ingest`, which re-triggers the workflow via the push trigger.

The actual block on merging is the PR staying in **draft**: GitHub disables the merge button on a draft PR regardless of any check's pass/fail state, and this repo's branch protection on `main` only restricts direct pushes (PRs are the only way in), it doesn't require this workflow's check to pass. So the comment is purely visibility, the draft state is what actually blocks.

Version bumps are scoped specifically to `src/localis/data` (the published dataset), separately from the broader "is there anything to commit at all" check, since the raw bookkeeping files (per-domain `*.manifest.json`, `resolution_map.json`, `orphaned_subdivisions.json`) can change independently of the dataset output and still need to be committed even when they do. On a run where the dataset itself changed, `poetry version minor` bumps it. Reasoning: strict semver would call a data refresh a patch (no API change), but this package's actual value is the data as much as the API, and a refresh almost always means *more* coverage rather than a fix to something broken, so a minor bump reads more honestly to a consumer. This is a routine, ongoing bump for as long as the project is at `1.0.0` or later; it's independent of the alpha/beta/stable phase transitions the maintainer manages by hand in `pyproject.toml`.

Cities is included in the pipeline (`ingest_all()` calls `ingest_cities()` again); no changes were needed in `ingest.yaml` for this since its dataset-changed and diff-stat checks are already scoped generically to `src/localis/data`, not per-domain.

Also fixed in passing, discovered while reviewing this: `release.yaml`'s `actions/checkout@v4` never fetched tags, so `git tag | sort --version-sort | tail -n1` always came back empty, meaning the workflow always believed no version had ever been released and would re-attempt publishing whatever version was already in `pyproject.toml`. That's what actually broke the most recent release run (PyPI rejects re-uploading an already-used filename), not a PyPI API deprecation. Fixed with `fetch-tags: true` on that checkout step. This matters here because merged `ingest` PRs are exactly the kind of `main` push that would trigger this failure mode again if it weren't fixed.

### Workflow: `.github/workflows/ingest.yaml`

Triggers: `schedule` (monthly cron, `0 6 1 * *`) and `push: branches: [ingest]` (this is also how a manual run happens, there's no separate `workflow_dispatch`). Guarded with `if: github.repository == 'dstoffels/localis'`, matching `release.yaml`'s existing pattern, since scheduled triggers otherwise also fire on forks.

Steps, following `test.yaml`'s existing conventions (`ubuntu-latest`, `actions/checkout@v4`, `actions/setup-python@v5` at `3.11`, `snok/install-poetry@v1`, `actions/cache@v3` keyed on `poetry.lock`):

1. Checkout `ref: ingest` with `fetch-depth: 0` (needed for the `HEAD~1` diff later; the default shallow clone would break it).
2. Set up Python/Poetry, configure `github-actions[bot]` git identity.
3. `poetry run ingest` (always exits `0`).
4. Bump version if `src/localis/data` changed (see above).
5. `git add -A`, check `git diff --cached --quiet` for whether there's anything to commit at all.
6. If yes: commit (message includes the new version when bumped) and `git push origin ingest`.
7. `poetry run check-orphans > orphan_summary.md`, capturing its exit code to know the current orphan state.
8. Ensure an `ingest` → `main` PR exists (`gh pr list` then `gh pr create --draft` if none found); only runs when step 5 found a diff.
9. If step 5 found a diff: post a comment with that run's actual changes (whether the version bumped, a `git diff --stat HEAD~1 HEAD -- src/localis/data` block), not a vague pointer at the commit history.
10. If orphans were found: comment with the `check-orphans` summary.
11. If no orphans were found: `gh pr ready` (unconditional on this alone, not also gated on step 5's diff, so a run that resolves the last orphan without any other upstream change still flips the PR out of draft).
12. If orphans were found: fail the job, after everything above has already run.

Needs `permissions: contents: write` and `pull-requests: write` (default `GITHUB_TOKEN` covers both).

### Verification

- Unit-level: done. `poetry run check-orphans` tested locally against both an empty and a populated `orphaned_subdivisions.json`.
- Workflow-level: not yet done. First real test requires pushing to `origin/ingest`, which triggers a genuine Actions run against the real repo.
- Still to confirm live: `gh pr list --head ingest --base main` shows at most one PR after repeated runs (idempotency), and it flips out of draft only when clean.