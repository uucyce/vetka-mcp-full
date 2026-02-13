# MARKER_140.RECON_WEB_CONTEXT_TOOLS
# Recon Report: Live Web Context into VETKA Viewport/Elisya/Tools (without heartbeat)

Date: 2026-02-13
Workspace: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
Scope: Recon only, no implementation

## 1) Core conclusion
Heartbeat is not the right mechanism for this feature.
Your target fits the existing message-context pipeline:
`frontend viewport payload -> Socket user_message -> backend context builders -> model prompt/tooling`.

So yes: we can feed active web page context to agents **before Save to VETKA**, and still keep Save as a separate persistence action.

## 2) Current context pipeline (as-is)

### Frontend send path
- File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/hooks/useSocket.ts`
- `sendMessage()` already sends:
  - `pinned_files`
  - `viewport_context` (from `buildViewportContext(...)`)
  - model routing data

### Viewport builder
- File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/utils/viewport.ts`
- `buildViewportContext(...)` produces camera + pinned + visible nodes.
- This is the correct place to keep spatial anchor data for “nearest node” logic.

### Backend intake of context
- File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/user_message_handler.py`
- Reads `pinned_files`, `viewport_context` from incoming message.
- Builds:
  - `pinned_context` via `build_pinned_context(...)`
  - `viewport_summary` via `build_viewport_summary(...)`
  - `json_context` via `build_json_context(...)`

### Compression + structured context
- File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/message_utils.py`
- `build_json_context(...)` already supports compressed/legend output and token budget.
- `build_pinned_context(...)` already uses unified weighting (Qdrant/CAM/Engram/Viewport/HOPE/MGC).

### Tool layer
- File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/tools/llm_call_tool.py`
- Safe tool allowlist exists for function-calling models.
- Can be extended with web-context tools if needed.

## 3) Where to integrate web-page context (best insertion points)

### A. Frontend: live web context carrier (pre-save)
Add `web_context` to outgoing `user_message` payload from `sendMessage()`.

Suggested shape:
```json
{
  "web_context": {
    "url": "https://...",
    "title": "...",
    "selection": "user selected text",
    "excerpt": "auto extracted 1-3KB",
    "source": "tauri_webview",
    "captured_at": "ISO-8601"
  }
}
```

### B. Backend: parse + summarize + optional expand
In `user_message_handler.py`:
- accept `web_context`
- pass it to prompt builders

In `message_utils.py`:
- new helper to render compact prompt block (`WEB CONTEXT SUMMARY`)
- optional “expand” hook if model asks for more details

### C. Tool system
Option 1 (minimal): no new tool, just auto summary in prompt.
Option 2 (recommended): add read-only tool for expansion (`get_active_web_context` / `expand_web_context`) in safe allowlist.

This gives low token baseline + on-demand depth.

## 4) Architecture recommendation (no Tavily dependency on hot path)

Primary path (fast, local, deterministic):
1. User opens page in Tauri web window
2. Frontend keeps latest extracted page context in memory
3. Chat message auto-includes compact `web_context`
4. Model sees context immediately

Optional enrichment path:
- Tavily only for external corroboration/fact-check when needed.
- Not required for immediate page understanding.

## 5) Nearest-node save strategy (when user clicks Save)
Use fallback chain:
1. First pinned node (if exists)
2. Selected node
3. Nearest visible node by camera-space distance (`viewport_context`)
4. Semantic nearest from Qdrant if 1-3 unavailable

Persist both formats:
- HTML snapshot
- MD extracted text

## 6) Marker plan for future implementation
- `MARKER_140.WEB_CTX_SCHEMA`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/hooks/useSocket.ts`
  - add `web_context` into `user_message` emit

- `MARKER_140.WEB_CTX_STATE`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/store/useStore.ts` (or dedicated web-context store)
  - keep active page context from Tauri window

- `MARKER_140.WEB_CTX_INGEST`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/user_message_handler.py`
  - ingest `web_context` and route into prompt build

- `MARKER_140.WEB_CTX_SUMMARY`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/message_utils.py`
  - compact summary + token guard + optional expand section

- `MARKER_140.WEB_CTX_TOOL`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/tools/llm_call_tool.py`
  - optional safe read-only expansion tool in allowlist

- `MARKER_140.WEB_CTX_SAVE_ANCHOR`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/artifact_routes.py`
  - bind saved web artifact to nearest node via viewport fallback chain

## 7) Risks and constraints
1. Prompt bloat if raw page text is injected directly each message.
- Mitigation: summary-first (1-3KB), expand on demand.

2. Privacy of page content.
- Mitigation: explicit toggle: "Share current web page with agents".

3. Multi-window consistency.
- Mitigation: include `window_id` and `captured_at`, choose freshest active context.

4. Model/tool behavior differences.
- Mitigation: keep base path tool-agnostic; tools only for expansion.

## 8) Answer to your design question
Yes, your idea is correct and implementable with existing VETKA stack:
- no heartbeat,
- no mandatory Tavily,
- live web context goes through the same viewport/Elisya pipeline,
- Save remains explicit persistence to VETKA graph/artifacts.
