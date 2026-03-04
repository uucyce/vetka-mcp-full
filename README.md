# VETKA

VETKA is a local-first knowledge graph workspace with:
- 3D graph navigation (VETKA)
- agent/runtime orchestration and memory layers (CAM/ARC/ELISION)
- semantic + file search with intent-aware retrieval

## Quick Start

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
source .venv/bin/activate
./run.sh
```

Backend API default: `http://127.0.0.1:5001`

## Public Module Repositories (Umbrella)

VETKA is being published as modular public repositories while keeping this
monorepo as source of truth.

| Module | Public Repo | Monorepo Source Prefix |
|---|---|---|
| MCP core | https://github.com/danilagoleen/vetka-mcp-core | `src/mcp` |
| Bridge core | https://github.com/danilagoleen/vetka-bridge-core | `src/bridge` |
| Search + retrieval | https://github.com/danilagoleen/vetka-search-retrieval | `src/search` |
| Memory stack | https://github.com/danilagoleen/vetka-memory-stack | `src/memory` |
| Ingest engine | https://github.com/danilagoleen/vetka-ingest-engine | `src/scanners` |
| Elisya runtime | https://github.com/danilagoleen/vetka-elisya-runtime | `src/elisya` |
| Orchestration core | https://github.com/danilagoleen/vetka-orchestration-core | `src/orchestration` |
| Chat UI | https://github.com/danilagoleen/vetka-chat-ui | `client/src/components/chat` |

Module sync notes and latest mirror SHAs are tracked in:
- `docs/160_git/MARKER_160_MODULE_REPOS_STATUS_2026-03-04.md`

## Search (Phase 157)

Current search stack supports:
- descriptive multi-word query intent (`>= 4 words` by default)
- file-first policy for explicit file-finder prompts (e.g. `"найди файл ..."`)
- JEPA-assisted reranking with safe fallback when embedding backend is unavailable

Key files:
- `src/search/file_search_service.py`
- `src/search/hybrid_search.py`
- `src/api/handlers/unified_search.py`

## Tests

```bash
pytest -q tests/test_phase157_search_ranking_regression.py \
          tests/test_phase157_hybrid_file_first_policy.py \
          tests/test_phase157_unified_search_descriptive_runtime.py
```

## Project Docs

Main docs are under:
- `docs/`
- `docs/157_ph/` (Phase 157 markers and runtime notes)

## License

This project is licensed under the [MIT License](LICENSE).
