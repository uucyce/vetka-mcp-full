# Phase 170 CUT Packaging Gate Split

## Scope

Task lanes:
- `tb_1773382600_246`
- `tb_1773382600_247`

## Problem

The default Tauri path still runs:

```bash
npm run build
```

That command executes shared `tsc && vite build` for the full client and is blocked by repo-wide TypeScript debt outside the CUT packaging lane.

## Minimal CUT-specific gate

To keep CUT app/dmg work moving without touching unrelated client modules:

- human review dev lane is pinned to `3011`
- dedicated launcher: `scripts/cut_dev_human.sh`
- dedicated Tauri config: `client/src-tauri/tauri.human.conf.json`
- dedicated build gate: `scripts/cut_build_human.sh`

## How the split works

`scripts/cut_build_human.sh` generates a temporary Vite entry that mounts only `CutStandalone` and then runs:

```bash
npx vite build --config /tmp/.../vite.cut-human.config.mjs
```

This avoids repo-wide `tsc` and avoids bundling the default `App` entry as the packaging gate.

## Intended outcomes

- `scripts/cut_dev_human.sh web` stays on `127.0.0.1:3011`
- `scripts/cut_dev_human.sh tauri-dev` uses the same reserved port
- `scripts/cut_dev_human.sh tauri-build` points Tauri at `dist-cut-human`
- CUT packaging can now be tested against a CUT-only frontend bundle path before broader client-wide TypeScript cleanup

## Residual risk

- this split is a packaging gate only, not a permanent architecture boundary
- if `CutStandalone` itself begins importing broken client-wide modules, the CUT-only gate will fail too
- the main full-app `npm run build` path remains blocked until shared TypeScript issues are fixed
