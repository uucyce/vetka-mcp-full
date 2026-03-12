# TaskBoard Governance V1

Tag: `localguys`, `taskboard`, `governance`

## Why

Parallel agents keep stopping on the same ambiguity:
- task belongs to one lane, but git tree is dirty elsewhere
- allowed edit surface is implied, not explicit
- done criteria are discussed ad hoc instead of enforced
- ownership is social, not machine-readable

This document turns that into a TaskBoard contract.

## Minimal required fields for TaskBoard V2

These four fields remove most false blocks:

1. `ownership_scope`
   - examples: `cut`, `mcc`, `tts`, `photo_parallax`, `shared`
   - tells the agent which lane owns the task

2. `allowed_paths`
   - explicit allowlist of files and globs
   - lets the agent continue safely even if the broader tree is dirty

3. `owner_agent`
   - examples: `codex`, `claude`, `human`, `shared`
   - clarifies who may execute and who should not mutate status

4. `completion_contract`
   - explicit done rules
   - examples: `vite build passes`, `playwright smoke passes`, `result_summary required`

## Recommended extended fields

- `verification_agent`
- `blocked_paths`
- `forbidden_scopes`
- `worktree_hint`
- `touch_policy`
- `overlap_risk`
- `depends_on_docs`

## Enforcement rules

### Creation gate
- a new execution task should not be created without `ownership_scope` and `allowed_paths`
- docs-only tasks may omit `allowed_paths` only when `touch_policy=safe_docs_only`

### Status gate
- if `owner_agent != current_agent`, status mutation is blocked except for `verification_agent`
- moving to `done` requires:
  - `result_summary`
  - `completed_at`
  - satisfied `completion_contract`

### MCC context packet
Governance fields must ride in the same dispatch packet as:
- roadmap binding
- workflow contract
- docs
- code scope
- tests
- artifacts

That lets MCC agents consume governance from the DAG-linked packet instead of inferring it from chat text.

## Example CUT task

```json
{
  "ownership_scope": "cut",
  "allowed_paths": [
    "client/src/CutStandalone.tsx",
    "client/src/components/cut/**",
    "src/api/routes/cut_routes.py",
    "tests/phase170/**"
  ],
  "blocked_paths": [
    "client/src/components/mcc/**",
    "src/api/routes/mcc_routes.py",
    "photo_parallax_playground/**"
  ],
  "owner_agent": "claude",
  "verification_agent": "codex",
  "worktree_hint": ".claude/worktrees/clever-kalam",
  "touch_policy": "frontend_cut_only",
  "overlap_risk": "low",
  "completion_contract": [
    "playwright smoke passes",
    "vite build passes",
    "result_summary required"
  ]
}
```

## Rollout order

1. ship V1 doc
2. add minimal fields to TaskBoard model and adapters
3. enforce ownership + done gate
4. enrich packet/MCC consumption with governance metadata
5. add extended fields and UI affordances
