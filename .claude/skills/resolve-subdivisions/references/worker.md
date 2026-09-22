# Resolve Subdivisions — Worker Instructions

You've been dispatched to resolve orphaned ISO 3166-2 subdivisions, ones localis's ingestion pipeline couldn't confidently auto-merge with a GeoNames counterpart via fuzzy string matching. Your job: use real-world geographic knowledge to decide each one with high confidence, or explicitly skip it for a human rather than guess.

## API

Everything goes through one CLI, invoked directly by path. DO NOT INVOKE ANY OTHER CLI COMMANDS OUTSIDE OF THIS DESIGNATED INTERFACE.

### next
- ref: `next`
- command: poetry run python .claude/skills/resolve-subdivisions/scripts/api.py next <page>

### merge
- ref: `merge`
- command: poetry run python .claude/skills/resolve-subdivisions/scripts/api.py merge <iso_code> <hashid> [--names NAME ...]

### add
- ref: `add`
- command: poetry run python .claude/skills/resolve-subdivisions/scripts/api.py add <iso_code> [--names NAME ...]

### skip
- ref: `skip`
- command: poetry run python .claude/skills/resolve-subdivisions/scripts/api.py skip <iso_code> "<reason>"

## Loop:

- DO NOT INVOKE ANY OTHER CLI COMMANDS OUTSIDE OF THIS DESIGNATED INTERFACE.
- Use real-world knowledge, not string similarity.

`MAX_CANDIDATES` = 300
`CANDIDATES_PROCESSED` = 0


1. IF `CANDIDATES_PROCESSED` >= `MAX_CANDIDATES`: 
   1. STOP. DO NOT INVOKE ANY OTHER CLI COMMANDS OUTSIDE OF THIS DESIGNATED INTERFACE.
2. `PAGE` = 1
3. CALL `next <PAGE>` to retrieve the next undecided orphaned subdivision and its first page of candidates.
   1. `CANDIDATES_PROCESSED` += <len(candidates)>
   2. IF `null`: 
      1. STOP. DO NOT INVOKE ANY OTHER CLI COMMANDS OUTSIDE OF THIS DESIGNATED INTERFACE.
   3. IF `candidates` IS EMPTY: 
      1. GOTO 4. DO NOT INVOKE ANY OTHER CLI COMMANDS OUTSIDE OF THIS DESIGNATED INTERFACE.
   4. IF you have high confidence that this ISO subdivision and one specific candidate are the same place (a transliteration difference, an old vs. current name, a local vs. official form, etc.). If multiple candidates share a name, use `admin_level` against the orphan's own `type` to pick the right one, not just the first match:
      1. CALL `merge <iso_code> <hashid> [--names NAME ...]`
      2. GOTO 1. DO NOT INVOKE ANY OTHER CLI COMMANDS OUTSIDE OF THIS DESIGNATED INTERFACE.
   5. ELSE: 
      1. `PAGE` += 1
      2. GOTO 3. DO NOT INVOKE ANY OTHER CLI COMMANDS OUTSIDE OF THIS DESIGNATED INTERFACE.
4. IF There is genuinely no matching GeoNames candidate for an existing subdivision, but the ISO subdivision exists in reality:
   1. CALL `add <iso_code> [--names NAME ...]`
   2. GOTO 1. DO NOT INVOKE ANY OTHER CLI COMMANDS OUTSIDE OF THIS DESIGNATED INTERFACE.
5. ELSE IF there is no suitable match and you need to defer the decision to a human reviewer because you are unsure, lack sufficient information or there appears to be a conflict or ambiguity:
   1. CALL `skip <iso_code> "<reason>"`
   2. GOTO 1. DO NOT INVOKE ANY OTHER CLI COMMANDS OUTSIDE OF THIS DESIGNATED INTERFACE.


## Guardrails

- DO NOT INVOKE ANY OTHER CLI COMMANDS OUTSIDE OF THIS DESIGNATED INTERFACE.
- NEVER READ OR EDIT `orphaned_subdivisions.json` or `resolution_map.json`
- Never fabricate a `hashid` — it must come from that specific entry's own `candidates` list; `merge` validates this and raises if it wasn't.
