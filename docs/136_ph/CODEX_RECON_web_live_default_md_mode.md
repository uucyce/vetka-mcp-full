# MARKER_139.RECON_WEB_LIVE_DEFAULT
# Recon Report: Artifact Web Live (Default) + MD Save Mode

Date: 2026-02-11
Workspace: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

## Scope
- Only client-side isolated files.
- No changes in `src/orchestration/`, `src/mcp/`, `src/services/`.

## What is already implemented
1. Web search results open in Artifact as `rawContent.type = "web"`.
- File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/App.tsx`

2. Artifact web renderer currently uses iframe by direct URL.
- File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/artifact/ArtifactPanel.tsx`

3. Browser/Tauri bridge exists with dynamic imports and runtime detection.
- File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/config/tauri.ts`

## Root cause of "white page"
1. Some websites forbid embedding (`X-Frame-Options` / CSP `frame-ancestors`).
- In these cases iframe cannot render full content, regardless of fetch snippet.

2. Current iframe sandbox is restrictive for session/cookie-heavy flows.
- Missing `allow-same-origin` breaks auth/session behavior on many sites.

## Non-duplication check
- Existing markers found and preserved:
  - `MARKER_139.S1_2_UNIFIED_ARTIFACT_FIX`
  - `MARKER_139.S1_3_WEB_FALLBACK`
- New implementation will add separate marker namespace to avoid overlap:
  - `MARKER_139.S1_4_WEB_LIVE_DEFAULT`

## Patch plan
1. Add web display mode state in Artifact panel:
- Default: `Live`
- Toggle: `MD`

2. Improve Live iframe settings for maximum compatibility:
- Add `allow-same-origin` and user-activation navigation permissions.

3. Add native Tauri live window opener (WebKit/WebView) via dynamic import:
- New helper in `client/src/config/tauri.ts`
- Trigger button from Artifact web header.

4. Keep MD mode as explicit fallback/save-friendly representation.
