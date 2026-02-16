# MARKER_144.PLAN_NATIVE_WEB_BROWSER

Date: 2026-02-13
Status: approved for implementation
Objective: align web-search UX with VETKA visual style and native browsing flow.

## Scope (Approved)

- Remove `SV` action from search result rows.
- In `web/` context, click on a result should open native Tauri web window directly.
- Keep search backend in unified API; do not route web viewing through Socket.IO.
- Improve result row readability (titles currently over-truncated).
- Preserve Nolan/Batman style: dark monochrome, minimal accents.

## MARKER_144.IMPL_STEP_1_UI_CLEANUP

Files:
- `client/src/components/search/UnifiedSearchBar.tsx`

Changes:
- remove inline `SV` button from rows;
- remove extra blue accent tied to save button;
- keep row actions minimal (open, pin);
- improve title/path rendering to reduce aggressive truncation.

## MARKER_144.IMPL_STEP_2_WEB_RESULT_NATIVE_OPEN

Files:
- `client/src/App.tsx`
- `client/src/components/chat/ChatPanel.tsx`

Changes:
- detect web result (`source==='web' || source starts with http`);
- if Tauri runtime: open via `openLiveWebWindow(url, title)` immediately on row click;
- if not Tauri: fallback to current artifact open path.

## MARKER_144.IMPL_STEP_3_READABILITY_FIX

Files:
- `client/src/components/search/UnifiedSearchBar.tsx`

Changes:
- web rows: reduce right-side metadata density;
- allow title to occupy more width (2-line clamp);
- keep path compact but readable;
- avoid large empty right gutters.

## MARKER_144.RESEARCH_STREAM_A (parallel)

Topic: Native browser session persistence (avoid re-login).

Questions:
1. Where does `open_research_browser` store profile/cookies now?
2. Is WebView profile persistent across app restarts on macOS/Windows?
3. Can we isolate a dedicated profile `vetka_research_profile`?

Likely files to inspect:
- `src-tauri/src/main.rs`
- tauri window setup / command `open_research_browser`
- `tauri.conf.json`

## MARKER_144.RESEARCH_STREAM_B (parallel)

Topic: Native browser top toolbar in VETKA style.

Questions:
1. Do we already have custom titlebar/webview overlay controls?
2. Best implementation path:
   - Rust native window chrome controls
   - HTML toolbar in companion window + WebView navigation bindings
3. Back/forward/find/page-save API availability via Tauri command bridge.

Design requirements:
- black panel;
- white simple icons;
- VETKA icon asset:
  `/Users/danilagulin/Documents/VETKA_Project/icons/vetka_gpt_1_UP1_PHalfa.png`;
- hover tooltip: `save to vetka`;
- click indicator ring around icon.

## MARKER_144.RESEARCH_STREAM_C (parallel)

Topic: 2-step save flow from native browser window.

Required behavior:
1. step 1 modal: name + format (HTML/MD);
2. step 2 modal: destination node/path (default: nearest viewport node);
3. save both:
   - into VETKA artifact/node,
   - to disk at selected directed-mode location.

Questions:
1. nearest-node resolver already available where?
2. which API already creates artifacts with explicit destination path?
3. whether HTML capture is full page source or sanitized snapshot.

## MARKER_144.IMPLEMENT_NOW_BOUNDARY

This turn implements only:
- Step 1 UI cleanup,
- Step 2 native-open behavior,
- Step 3 readability fix.

This turn does NOT implement (research-dependent):
- full custom native toolbar,
- persistent profile refactor,
- two-step browser save dialog.

Those move to Phase 137.B after research streams A/B/C complete.

## Acceptance Criteria (current turn)

1. No `SV` button in search rows.
2. In `web/` search, row click opens native Tauri browser window when available.
3. Web result text in list is visibly more readable (less truncation, less empty space).
4. Existing vetka/file behavior is not regressed.

## Implementation Status (this turn)

- `MARKER_144.IMPL_STEP_1_UI_CLEANUP`: completed
  - removed `SV` from search rows;
  - removed blue save accent from result list.
- `MARKER_144.IMPL_STEP_2_WEB_RESULT_NATIVE_OPEN`: completed
  - web-result row click now opens native Tauri browser window when runtime is Tauri;
  - browser fallback keeps artifact preview behavior.
- `MARKER_144.IMPL_STEP_3_READABILITY_FIX`: completed
  - web rows now use denser layout (less right-side metadata noise);
  - title visibility improved with 2-line clamp and wider left content area.
