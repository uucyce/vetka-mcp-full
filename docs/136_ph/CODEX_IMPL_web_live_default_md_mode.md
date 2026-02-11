# MARKER_139.IMPL_WEB_LIVE_DEFAULT
# Implementation Report: Artifact Live Default + MD Mode + Native WebView

Date: 2026-02-11
Workspace: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

## Files changed
1. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/artifact/ArtifactPanel.tsx`
2. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/config/tauri.ts`

## What changed
1. Web artifacts now have explicit mode switch:
- `LIVE` (default)
- `MD` (manual fallback/preservation)

2. Live iframe compatibility improved:
- `sandbox` now includes `allow-same-origin` and user-activation navigation permissions.
- `referrerPolicy` set to `strict-origin-when-cross-origin`.

3. Native desktop fallback added for blocked sites:
- New helper `openLiveWebWindow(url, title?)` in `tauri.ts`.
- Uses dynamic import of `@tauri-apps/api/webviewWindow`.
- Artifact web header now has `NATIVE WINDOW` button (only in Tauri runtime).

## Why this solves current issue
- White pages from iframe embedding restrictions remain possible for some domains.
- For those, user can open full live page in native Tauri WebView where frame restrictions do not apply like in iframe embedding.
- MD mode remains available for knowledge capture and storage flow.

## Notes
- No backend/orchestration/mcp/services files changed.
- Existing unrelated TypeScript errors remain in repository and are outside this patch scope.
