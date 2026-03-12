# PHASE 170 CUT Launch And Port Protocol (2026-03-13)

## What "stable way to open CUT" means

It does **not** mean VPN broke my code context. It means every agent and every human review should know a fixed launch entrypoint and a fixed reserved port, instead of re-discovering a random Vite port after each restart.

## Problem

Without a launch protocol:
- one agent starts CUT on a random port
- another agent starts a second Vite server
- browser smoke or screenshot automation binds to the wrong instance
- Playwright/MCP/browser lanes become hard to reason about

## Protocol

### MARKER_170.LAUNCH.HUMAN_REVIEW
Human review lane:
- reserved port: `3011`
- purpose: manual CUT review only

### MARKER_170.LAUNCH.OPUS_SANDBOX
Claude Opus packaging sandbox:
- reserved port: `3111`
- purpose: launch/build/package experiments only
- script: `scripts/cut_dev_opus.sh`
- tauri config: `client/src-tauri/tauri.opus.conf.json`

### MARKER_170.LAUNCH.CODEX54_SANDBOX
Codex 5.4 High fixture/bootstrap sandbox:
- reserved port: `3211`
- purpose: Berlin sample fixture, browser smoke, bootstrap validation

## Rules

1. Each agent uses only its reserved port.
2. No agent reuses the human review port.
3. Browser smoke and screenshots must point to the reserved port for that sandbox.
4. If a sandbox cannot bind its reserved port, fail fast and report instead of auto-hopping to a random port.

## Why this matters

This is a coordination rule, not just infra hygiene. It prevents one agent from accidentally "stealing" another agent's browser target or Playwright lane.

## Exact Opus sandbox entrypoints

### Port check
```bash
scripts/cut_dev_opus.sh check-port
```

### Browser-only CUT sandbox on reserved port
```bash
scripts/cut_dev_opus.sh web
```

### Tauri dev sandbox on reserved port
```bash
scripts/cut_dev_opus.sh tauri-dev
```

### Tauri build attempt in the sandbox lane
```bash
scripts/cut_dev_opus.sh tauri-build
```

## Fail-fast rule

- if `3111` is already occupied, the Opus script must exit instead of choosing another port
- no shared live browser lane should be reused for packaging smoke or Tauri dev
