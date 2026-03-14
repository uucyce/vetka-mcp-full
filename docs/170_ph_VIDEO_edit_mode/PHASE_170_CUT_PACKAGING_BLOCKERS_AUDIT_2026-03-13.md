# Phase 170 CUT Packaging Blockers Audit

## Scope

Task lane: `tb_1773380000_233`

Focus:
- exact blockers for CUT app / dmg work
- repo-wide TypeScript and packaging issues outside the CUT lane
- no attempted fixes inside blocked CUT UI files

## Commands run

```bash
cd client && npm run build
cd client/src-tauri && cargo tauri build
cd client && npm run tauri:build:cut:opus
scripts/cut_dev_opus.sh web
```

Date of audit: 2026-03-13

## Primary blocker

The first hard blocker is not Tauri itself. It is the shared frontend build:

- `npm run build` fails in `tsc`
- `cargo tauri build` immediately fails for the same reason because `beforeBuildCommand` calls `npm run build`

This means CUT packaging is currently blocked before any app bundling or dmg-specific step is exercised.

## Tauri-specific warning already visible

- `client/src-tauri/tauri.conf.json` uses identifier `ai.vetka.app`
- Tauri warns that an identifier ending with `.app` is not recommended on macOS because it collides with the application bundle suffix

This warning is not the main blocker, but it is real packaging hygiene debt.

## High-signal blocker clusters

### Cluster A: app-shell typing drift
- `client/src/App.tsx`
- symptoms:
  - missing `chatMode`
  - missing `hasActiveGroup`
  - stale `autoListenAfter` property

### Cluster B: artifact viewer prop/type mismatches
- `client/src/components/artifact/ArtifactViewer.tsx`
- `client/src/components/devpanel/ArtifactViewer.tsx`
- symptoms:
  - invalid `language` prop
  - invalid `src` prop
  - missing `../../services/api`

### Cluster C: chat / MCC strict TypeScript backlog
- `client/src/components/chat/*`
- `client/src/components/mcc/*`
- symptoms:
  - implicit `any`
  - JSX namespace issue
  - invalid SVG props
  - stale unions / impossible comparisons

### Cluster D: Tauri bridge typing debt
- `client/src/config/tauri.ts`
- symptoms:
  - repeated `Untyped function calls may not accept type arguments`
  - implicit `event` typing failures

### Cluster E: hook / dependency drift
- `client/src/hooks/useArtifactMutations.ts`
- missing module: `@tanstack/react-query`

## CUT-lane implication

- current CUT packaging work should not try to fix all repo-wide TS errors from this lane
- the correct near-term move is to keep an isolated Opus sandbox path ready on `3111`, then hand off the actual TypeScript unblockers to the relevant owners

## Recommended unblock order

1. Fix the top-level `App.tsx` and `config/tauri.ts` type regressions
2. Fix missing/incorrect artifact viewer prop types
3. Restore missing dependency or remove dead `useArtifactMutations` path
4. Sweep the large `chat` / `mcc` implicit-`any` backlog
5. Re-run `npm run build`
6. Only then re-run `cargo tauri build`

## Packaging status

- CUT sandbox launch path on reserved port can be prototyped
- reserved-port browser launch was validated on `127.0.0.1:3111`
- app / dmg packaging is still blocked by frontend compile failures before bundle generation
