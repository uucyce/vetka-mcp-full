# MARKER_160_OPENSOURCE_USAGE_AUDIT_2026-03-06

Date: 2026-03-06
Scope: quick internal recon of monorepo (`src`, `client`, `data/templates`, `docs`)
Method: targeted `rg` search + direct file inspection

## 1) Directly integrated OSS/runtime dependencies (code-level)

Evidence is explicit in license/credits manifests:

- Root dependency notice:
  - `THIRD_PARTY_NOTICES.md`
- Module attributions:
  - `src/mcp/OPEN_SOURCE_CREDITS.md`
  - `src/bridge/OPEN_SOURCE_CREDITS.md`
  - `src/search/OPEN_SOURCE_CREDITS.md`
  - `src/orchestration/OPEN_SOURCE_CREDITS.md`
  - `src/elisya/OPEN_SOURCE_CREDITS.md`
  - `client/src/components/mcc/OPEN_SOURCE_CREDITS.md`

Confirmed examples:

- Protocol/runtime: MCP SDK, FastAPI/Starlette/Uvicorn, HTTPX, websockets/socketio
- Retrieval: Qdrant, Weaviate, RRF
- Orchestration: LangGraph, NetworkX
- Frontend/UI: React, TypeScript, React Flow, Framer Motion, react-draggable

## 2) Explicit "inspired/pattern" usage (architecture/templates)

### n8n / ComfyUI

- `src/services/converters/n8n_converter.py`
  - header: `n8n ↔ VETKA Workflow Converter`
  - explicit n8n type maps (`n8n-nodes-base.*`, `@n8n/...`)
- `src/services/converters/comfyui_converter.py`
  - header: `ComfyUI ↔ VETKA Workflow Converter`
  - explicit ComfyUI format mapping
- `src/orchestration/dag_executor.py`
  - docstring: `Architecture (inspired by n8n WorkflowExecute + ComfyUI execution.py)`

Conclusion: n8n/ComfyUI patterns are intentionally integrated as converter/execution references.

### OpenHands / G3 / Ralph-loop

- `data/templates/workflows/openhands_collab_stub.json`
  - `OpenHands-style Collaborative Loop (Stub)`
  - `OpenHands-inspired ...` in description
- `data/templates/workflows/g3_critic_coder.json`
  - `pattern_source: "block.xyz g3 paper + dhanji/g3"`
- `data/templates/workflows/ralph_loop.json`
  - `pattern_source: "snarktank/ralph"`
- `src/services/architect_prefetch.py`
  - references `openhands_patterns_v1`, `openhands_collab_stub`

Conclusion: these are template/policy inspirations in workflow presets, not vendored upstream code trees.

## 3) Mentions found but not evidence of code borrowing

- `Perplexity` appears in provider/key registry contexts:
  - `src/elisya/provider_registry.py`
  - `src/elisya/api_key_detector.py`
  - `src/utils/unified_key_manager.py`
- `Cursor` appears mainly as tool/client integration and internal docs/comments.

Conclusion: these matches indicate integration support (provider/client), not direct code import from those products.

## 4) Not found as concrete code integrations in this recon

No direct code-level evidence found for:

- `OpenClaw` / `OpenClaw aliases`
- `OpenDevin` direct integration

(Only possible doc mentions/noisy text; no concrete adapter/converter/module found in inspected paths.)

## 5) Risk note

This is a fast recon, not a full legal attribution audit. For public release hardening, run a follow-up pass:

1. validate each `pattern_source` with exact upstream URL + license note;
2. ensure `OPEN_SOURCE_CREDITS.md` exists in every extracted public module;
3. keep `THIRD_PARTY_NOTICES.md` regenerated from lockfiles before release tag.

## 6) Short verdict

- VETKA already contains solid attribution scaffolding.
- Strongest explicit ecosystem links in code today: **LangGraph, n8n, ComfyUI, OpenHands-style/G3/Ralph-loop templates, MCP/Qdrant/Weaviate**.
- `OpenClaw` does **not** currently appear as a concrete integrated module in inspected code.
