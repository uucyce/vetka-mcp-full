# MARKER_145.RECON_VIEWPORT_BROWSER_SAVE

Date: 2026-02-13
Status: in progress (partial implementation delivered)
Objective: connect web search -> native web window -> directed save with viewport-aware default anchor in VETKA style.

## MARKER_145.CURRENT_STATE

What is already working:
- web results open native Tauri web window directly from unified search click.
- web context has priority in chat prompt pipeline while viewport context is preserved.
- unified web search supports provider capabilities + Tavily/Serper + RRF merge.

Current UX gaps:
- native web window has no custom VETKA top toolbar yet (back/forward/address/find/save).
- save flow is still one-click; no explicit 2-step modal chain (name/format -> destination).
- default save destination previously ignored viewport nearest node.

## MARKER_145.IMPLEMENTED_NOW

### 1) Directed save anchor from viewport
Files:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/artifact/ArtifactPanel.tsx`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/artifact_routes.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/artifact_routes.py`

Changes:
- frontend computes recommended `target_node_path` from current viewport (center/nearest file|folder with pinned priority).
- `save-webpage` now sends `target_node_path`, `file_name`, `output_format`.
- backend accepts those fields and resolves actual save directory from node path (directed mode friendly).

Result:
- save goes to disk near the nearest viewport node by default (when available), while still being indexed by VETKA as artifact.

### 2) Web toolbar style alignment (dark monochrome)
Files:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/artifact/ArtifactPanel.tsx`

Changes:
- removed blue accents from web preview controls and link styling.
- normalized to grayscale Nolan/VETKA palette for `NATIVE WINDOW` and `SAVE TO VETKA` controls.

### 3) Search row readability follow-up
Files:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/search/UnifiedSearchBar.tsx`

Changes:
- web rows hide extra right-side metadata/source badges.
- tighter right block spacing so titles keep more width.

## MARKER_145.RESEARCH_A_NATIVE_TOOLBAR

Research needed before implementation:
- best architecture for true browser-like controls while preserving site compatibility.

Decision notes:
- `WebviewUrl::External(url)` gives best site compatibility and persistent session behavior, but no in-page custom toolbar.
- app-route + iframe toolbar gives custom UI, but many sites block iframe (X-Frame-Options/CSP).

Recommended implementation path:
1. Keep external webview as rendering surface.
2. Add small companion control window (VETKA toolbar) bound to webview commands via Tauri events.
3. If command API lacks nav controls, implement plugin/JS bridge for back/forward/reload/find.

## MARKER_145.RESEARCH_B_SESSION_PERSISTENCE

Research needed:
- explicit profile/session persistence guarantees per OS for Tauri 2 WebView.
- separation between main app session and research browser profile.
- security policy for preserving auth sessions (Gmail/xAI/social).

Target output:
- documented profile path policy + cleanup/reset command.

## MARKER_145.RESEARCH_C_TWO_STEP_SAVE_DIALOG

Research needed:
- reuse existing VETKA modal system or create dedicated modal component in black theme.
- support exact 2-step flow:
  1. `name + format (HTML|MD)`
  2. `destination` (default nearest viewport node, user-editable path)
- define final payload contract for both backend and native browser window save action.

Proposed API contract:
- `POST /api/artifacts/save-webpage` body:
  - `url`, `title`, `snippet`, `file_name`, `output_format`, `target_node_path`
- response:
  - `success`, `file_path`, `filename`, `format`, `target_node_path`

## MARKER_145.NEXT_IMPL_BATCH

Planned next implementation batch (after research A/B/C):
1. Add VETKA native toolbar window with icon `/Users/danilagulin/Documents/VETKA_Project/icons/vetka_gpt_1_UP1_PHalfa.png`.
2. Add two-step save modals in same visual language.
3. Wire nearest-node default into destination step with manual override.
4. Persist browser sessions with explicit profile strategy and reset option.
