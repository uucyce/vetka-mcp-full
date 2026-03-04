# MARKER_160 - Module Repos Status (2026-03-04)

## Scope
Unified status snapshot after deep documentation/positioning pass for public module repositories.

## Source of truth
- Monorepo: `danilagoleen/vetka`
- Branch used for changes: `codex/mcc-wave-d-runtime-closeout`
- Publishing model: `git subtree split --prefix=<module> ...` -> force-push into module `main`

## Module Matrix

| Order | Module Repo | Monorepo Prefix | Main SHA | Status |
|---|---|---|---|---|
| 1 | `vetka-mcp-core` | `src/mcp` | `3feb47e0a4b7ce5104e24146fb4d03f4e51077e1` | synced |
| 2 | `vetka-bridge-core` | `src/bridge` | `62217663ef5c3f8345b7e40bfb91aa14d64c3347` | synced |
| 3 | `vetka-search-retrieval` | `src/search` | `214ba4352c170fa962c2397597f0270085019d46` | synced |
| 4 | `vetka-memory-stack` | `src/memory` | `da0e2245c41384604c5df284c657b4fbfa85cb4c` | synced |
| 5 | `vetka-ingest-engine` | `src/scanners` | `bd6ea84ed4c04339f99dbe826b3362f925f2d259` | synced |
| 6 | `vetka-elisya-runtime` | `src/elisya` | `26a821b8543155f717d9eb5016f49ea181b50238` | synced |
| 7 | `vetka-orchestration-core` | `src/orchestration` | `483a2cc8cd88ce9a2582b32dec2465ab5d58e348` | synced |
| 8 | `vetka-chat-ui` | `client/src/components/chat` | `7bb160613017ed3628fbd5c3035b70091174572f` | synced |

## What was standardized in each module
- README rewritten from generic to architecture/value-oriented positioning.
- CHANGELOG bumped with `0.1.1` docs/positioning update entry.
- `OPEN_SOURCE_CREDITS.md` added with upstream attribution references.
- GitHub repository metadata updated:
  - richer description,
  - focused topics for discoverability.

## Guardrails used
- Only module-specific files were staged for each commit.
- No destructive git commands were used.
- Subtree publishing preserved monorepo as source-of-truth and avoided duplicate manual edits in module repos.

## Follow-up (recommended)
1. Add one umbrella index page in root `vetka` README linking all module repos.
2. Start semantic version tags in each module repo (`v0.1.1` baseline).
3. Add minimal CI badge/workflow per module (lint + smoke test).
