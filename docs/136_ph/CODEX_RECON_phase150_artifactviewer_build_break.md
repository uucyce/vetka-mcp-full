# MARKER_136.RECON.BUILD_BREAK_ARTIFACTVIEWER
# Recon Report: client build failure at ArtifactViewer.ts line 1

Date: 2026-02-15  
Workspace: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

## Objective
Identify root cause of:
- `npm --prefix client run build` failure
- `src/components/artifact/ArtifactViewer.ts(1,1): error TS1434 ...`

## Recon Evidence
1. File content is non-code
- Path: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/artifact/ArtifactViewer.ts`
- Line 1 starts with prose text:
  - `Looking at the ArtifactViewer component, I can see...`
- File contains pasted patch/diff text block, not valid TypeScript module.

2. Why TypeScript compiles this file
- `client/tsconfig.json` has:
  - `"include": ["src"]`
- Any `.ts/.tsx` file under `client/src` is part of compilation.
- Therefore invalid `ArtifactViewer.ts` breaks the build immediately.

3. Name collision context
- ArtifactViewer variants currently present:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/artifact/ArtifactViewer.ts` (invalid text)
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/artifact/ArtifactViewer.tsx` (component)
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/artifact/viewers/ArtifactViewer.tsx` (another component)
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/panels/ArtifactViewer.tsx` (panel component)

## Root Cause (no-guess)
- Build fails because `ArtifactViewer.ts` is an accidentally committed/generated text artifact in compile scope (`client/src`).

## Minimal Safe Fix Proposal (for GO)
- Remove or move `client/src/components/artifact/ArtifactViewer.ts` out of `client/src`.
- Keep runtime components untouched (`.tsx` files).
- Re-run `npm --prefix client run build`.

## Marker Set
- `MARKER_136.RECON.BUILD_BREAK_ARTIFACTVIEWER`
