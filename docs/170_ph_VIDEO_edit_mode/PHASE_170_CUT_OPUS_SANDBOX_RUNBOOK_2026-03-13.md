# Phase 170 CUT Opus Sandbox Runbook

## Scope

Task lanes:
- `tb_1773380000_234`
- `tb_1773380000_235`

Sandbox identity:
- hint: `opus_cut_packaging_sandbox`
- reserved port: `3111`
- no shared browser lane

## Files

- launch script: `scripts/cut_dev_opus.sh`
- package scripts: `client/package.json`
- tauri config override: `client/src-tauri/tauri.opus.conf.json`
- launch protocol: `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_LAUNCH_AND_PORT_PROTOCOL_2026-03-13.md`
- blocker audit: `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_PACKAGING_BLOCKERS_AUDIT_2026-03-13.md`

## Intended flows

### 1. Check the reserved port
```bash
scripts/cut_dev_opus.sh check-port
```

Expected:
- `FREE:3111` before launch
- if busy, stop and investigate; do not hop to another port

### 2. Launch browser-only sandbox
```bash
scripts/cut_dev_opus.sh web
```

What this does:
- starts Vite on `127.0.0.1:3111`
- refuses to run if `3111` is already occupied

### 3. Launch Tauri dev sandbox
```bash
scripts/cut_dev_opus.sh tauri-dev
```

What this does:
- uses `client/src-tauri/tauri.opus.conf.json`
- binds Tauri dev to `http://127.0.0.1:3111`
- keeps the Opus packaging lane isolated from human review and Codex lanes

### 4. Attempt Tauri build
```bash
scripts/cut_dev_opus.sh tauri-build
```

Current expected outcome:
- build is blocked by repo-wide TypeScript failures during `npm run build`
- this is still useful as a reproducible prototype path

## Current prototype status

### Works
- dedicated Opus Tauri config exists
- dedicated `3111` launch path exists
- fail-fast port lock exists in the launch script
- `scripts/cut_dev_opus.sh web` was validated to bind `http://127.0.0.1:3111/`

### Blocked
- `cargo tauri build` cannot complete until `npm run build` succeeds
- current blockers are documented in the packaging blockers audit

## Rules for future runs

1. never use `3011` or `3211` from this sandbox
2. never attach to an already-running random Vite instance
3. if `3111` is busy, exit and report
4. keep CUT UI code out of scope for this packaging runbook unless explicitly reassigned
