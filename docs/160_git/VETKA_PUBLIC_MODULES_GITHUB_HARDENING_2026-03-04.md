# VETKA Public Modules - GitHub Hardening (2026-03-04)

## Scope
Applied repository bootstrap metadata to all modular mirrors sourced from monorepo prefixes.

Modules:
- vetka-mcp-core (`src/mcp`)
- vetka-bridge-core (`src/bridge`)
- vetka-search-retrieval (`src/search`)
- vetka-memory-stack (`src/memory`)
- vetka-ingest-engine (`src/scanners`)
- vetka-elisya-runtime (`src/elisya`)
- vetka-orchestration-core (`src/orchestration`)
- vetka-chat-ui (`client/src/components/chat`)

## Completed Now
For each module prefix, added:
- `README.md`
- `LICENSE` (MIT)
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `SECURITY.md`
- `CHANGELOG.md`
- `.gitignore`
- `.github/pull_request_template.md`
- `.github/ISSUE_TEMPLATE/bug_report.md`
- `.github/ISSUE_TEMPLATE/feature_request.md`

This guarantees that subtree-published mirrors include baseline OSS/community scaffolding, not only source code.

## Still Required in GitHub UI (Manual)
1. Set repository description for each mirror.
2. Add topics (5-10/module).
3. Enable Issues and Discussions.
4. Enable branch protection on `main`.
5. Add initial release tags (for example `v0.1.0`) after first stable pass.
6. Add repo-level About links (documentation/homepage).

## Suggested Topics by Module
- vetka-mcp-core: `mcp`, `model-context-protocol`, `python`, `ai-tools`, `vetka`
- vetka-bridge-core: `agent-bridge`, `python`, `integration`, `automation`, `vetka`
- vetka-search-retrieval: `semantic-search`, `hybrid-search`, `retrieval`, `python`, `qdrant`
- vetka-memory-stack: `ai-memory`, `vector-memory`, `qdrant`, `weaviate`, `python`
- vetka-ingest-engine: `data-ingestion`, `embeddings`, `indexing`, `python`, `multimodal`
- vetka-elisya-runtime: `llm-routing`, `inference-runtime`, `provider-registry`, `python`, `ai`
- vetka-orchestration-core: `orchestration`, `dag`, `agentic-workflows`, `python`, `runtime`
- vetka-chat-ui: `react`, `typescript`, `chat-ui`, `frontend`, `ai-chat`

## Notes
- Source of truth remains monorepo `danilagoleen/vetka`.
- Mirrors are updated by `scripts/release/publish_public_mirrors.sh`.
