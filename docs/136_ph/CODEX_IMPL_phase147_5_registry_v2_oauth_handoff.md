# Phase 147.5 — Registry v2 + OAuth Handoff (Implemented)

## Markers
- MARKER_147_5_REGISTRY_V2_COMPAT
- MARKER_147_5_OAUTH_REAL_HANDOFF
- MARKER_147_5_OAUTH_CALLBACK_BRIDGE
- MARKER_147_5_TAURI_DEEPLINK_EVENT
- MARKER_147_5_OAUTH_START_REAL
- MARKER_147_5_OAUTH_TOKEN_EXCHANGE
- MARKER_147_5_SCANPANEL_OAUTH_HANDOFF
- MARKER_147_5_SCANPANEL_OAUTH_POLL

## What changed

### 1) Registry v2 (compat-safe)
Files:
- `data/connectors_registry.json`
- `src/services/connectors_state_service.py`

Done:
- Kept list-based `providers` format (compatible with existing loader).
- Added v2 metadata fields:
  - `provider_class`, `auth_flow`
  - `scopes_minimal`, `scopes_full`, `default_scopes`
  - `compliance_notes`, `rate_limit_policy`
- Added Wave A expansion entry: `telegram`.
- Added loader compatibility for both list and map registry forms.

### 2) OAuth real handoff (removed dev auto-complete)
File:
- `src/api/routes/connectors_routes.py`

Done:
- Removed pseudo OAuth behavior (`dev_auto_complete`).
- `POST /api/connectors/{provider_id}/oauth/start` now:
  - validates OAuth provider,
  - resolves client credentials from env,
  - builds provider authorize URL (Google/Dropbox/GitHub),
  - stores pending state with TTL.
- `POST /api/connectors/oauth/complete` now:
  - validates state/provider,
  - exchanges auth code for tokens,
  - stores OAuth bundle (`access_token`, optional `refresh_token`, `expires_in`, `scope`) in secure store,
  - marks connector connected.
- Added `GET /api/connectors/oauth/callback` bridge page for browser redirect completion.

### 3) ScanPanel OAuth UX
File:
- `client/src/components/scanner/ScanPanel.tsx`

Done:
- OAuth connect now opens real `auth_url` in Tauri external web window (or browser fallback).
- Removed immediate local `/oauth/complete` fake flow.
- Added background polling to refresh provider state after callback completion.
- Extended connector typing for registry v2 fields.

### 4) Tauri deep-link bridge
Files:
- `client/src-tauri/Cargo.toml`
- `client/src-tauri/tauri.conf.json`
- `client/src-tauri/src/main.rs`
- `client/src/config/tauri.ts`

Done:
- Added Tauri deep-link plugin + scheme config (`vetka`).
- Wired native deep-link open events to frontend event `oauth-deep-link`.
- Added frontend listener helper `onOAuthDeepLink(...)`.
- ScanPanel now completes OAuth on deep-link callback (`vetka://oauth/callback?code=...&state=...`).

### 5) Secure store enhancement
File:
- `src/services/connectors_secure_store.py`

Done:
- Added `set_oauth_tokens(...)` and `get_oauth_bundle(...)`.
- Preserved backward compatibility with existing `set_token/get_token` usage.

## Validation
- `python3 -m py_compile` passed for:
  - `src/api/routes/connectors_routes.py`
  - `src/services/connectors_state_service.py`
  - `src/services/connectors_secure_store.py`
- `pytest -q tests/test_phase147_5_connectors_oauth.py` passed (`3 passed`).
- TypeScript check:
  - `ScanPanel.tsx` has no new TS errors.
  - Pre-existing unrelated `TS6133` remain in other files.
- `cargo check` could not be completed in sandbox due network/DNS to crates.io (dependency fetch blocked).

## Notes
- Real provider exchange requires env credentials (per provider/class):
  - `GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET` (or provider-specific variants)
  - `DROPBOX_CLIENT_ID/DROPBOX_CLIENT_SECRET`
  - `GITHUB_CLIENT_ID/GITHUB_CLIENT_SECRET`
- Current callback bridge uses backend URL redirect target by default; deep-link-native completion can be layered as next subphase.
