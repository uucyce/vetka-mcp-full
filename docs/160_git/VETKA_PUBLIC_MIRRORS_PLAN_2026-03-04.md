# VETKA Public Mirrors Plan (Wave 1)

Date: 2026-03-04
Goal: one source of truth (private monorepo), public modular mirrors auto-updated from it.

## 1) First Public Repos

Owner: `danilagoleen`
Default branch for mirrors: `main`

1. `vetka-mcp-core`
- Why first: already modular in practice, high external contributor value.

2. `vetka-bridge-core`
- Why first: shared tooling layer for MCP/IDE integration.

3. `vetka-search-retrieval`
- Why first: clear standalone functionality, high OSS interest.

4. `vetka-memory-stack`
- Why first: core differentiation (CAM/ENGRAM/MGC/ELISION/STM).

5. `vetka-ingest-engine`
- Why first: scanner/watcher/extractor/vectorization pipeline.

6. `vetka-elisya-runtime`
- Why first: provider/middleware/model/key runtime.

7. `vetka-orchestration-core`
- Why first: ELISYA orchestration substrate (without full app shell).

8. `vetka-chat-ui`
- Why first: focused front-end contribution lane for chat UX.

## 2) Directory -> Repo Mapping

| Monorepo Prefix | Public Repo | Branch |
|---|---|---|
| `src/mcp` | `vetka-mcp-core` | `main` |
| `src/bridge` | `vetka-bridge-core` | `main` |
| `src/search` | `vetka-search-retrieval` | `main` |
| `src/memory` | `vetka-memory-stack` | `main` |
| `src/scanners` | `vetka-ingest-engine` | `main` |
| `src/elisya` | `vetka-elisya-runtime` | `main` |
| `src/orchestration` | `vetka-orchestration-core` | `main` |
| `client/src/components/chat` | `vetka-chat-ui` | `main` |

## 3) Automation Strategy

- Source of truth: this monorepo only.
- Public repos are mirrors updated by CI (not edited manually).
- Publishing mechanism: `git subtree split --prefix=<path>` + force push to mirror branch.
- If mirror repo does not exist, CI auto-creates it (private/public controlled by flag).

## Operational Rules

1. No direct commits to mirror repos.
2. Mirror repos are branch-protected (`main`), CI bot is the only writer.
3. Breaking contract changes require explicit version note in monorepo changelog.
4. If split fails for one module, other mirrors continue (best-effort publish).

