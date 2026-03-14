# CODEX IMPL REPORT: Phase 147.3 Connectors OAuth/Secure/Ingestion

Date: 2026-02-13  
Status: Implemented (backend-first, UI-compatible)

## MARKER_147.3_SECURE_STORE
Added secure token storage abstraction:

- New file: `src/services/connectors_secure_store.py`
- Stores connector tokens in `data/connectors_tokens.json`
- Encryption mode:
  - uses `cryptography.Fernet` when `ENCRYPTION_KEY` is available
  - fallback mode uses base64 encoding (explicitly marked as fallback in API/UI)
- API-facing capabilities:
  - `set_token()`, `clear_token()`, `has_token()`, `get_token()`
  - `encryption_enabled()`

## MARKER_147.3_INGESTION_QUEUE
Added queue service for Mycelium-facing scan jobs:

- New file: `src/services/connectors_ingestion_service.py`
- Queue file: `data/connectors_ingestion_queue.json`
- Supports:
  - enqueue connector ingestion jobs
  - list recent jobs

## MARKER_147.3_OAUTH_ROUTES
Extended connectors API in `src/api/routes/connectors_routes.py`:

1. OAuth-ready flow:
- `POST /api/connectors/{provider_id}/oauth/start`
- `POST /api/connectors/oauth/complete`

2. Status enrichment:
- `GET /api/connectors/status` now returns:
  - `token_present` per provider
  - `secure_storage_enabled` global flag

3. Scan → queue bridge:
- `POST /api/connectors/{provider_id}/scan` now:
  - updates scan metadata
  - enqueues ingestion job
  - emits Socket.IO event `connector_scan_enqueued` (best effort)
  - returns `ingestion_job_id`

4. Queue inspection:
- `GET /api/connectors/jobs`

## MARKER_147.3_SCANPANEL_BRIDGE
Updated `client/src/components/scanner/ScanPanel.tsx`:

- `connect` action now runs OAuth dev bridge:
  - `oauth/start` -> `oauth/complete`
- connector cards show:
  - token state (`token: saved|missing`)
  - secure storage mode (`secure store: on|fallback`)

Updated styles in `client/src/components/scanner/ScanPanel.css` for new status chips.

## MARKER_147.3B_AUTH_MENU
Extended Connect flow to explicit auth scenarios:

- `Auth` action now opens modal with method selection:
  - `OAuth`
  - `API key`
  - `Link`
- For `API key/Link`, user pastes value and frontend calls:
  - `POST /api/connectors/{provider_id}/auth/manual`
- Provider cards now treat `connected + token_missing` as `needsAuth`,
  showing `Auth` button instead of implicit trust.

## MARKER_147.3_VALIDATION
Checks run:

1. Python compile:
- `python -m py_compile ...` for all new/changed connector services/routes
- Result: OK

2. TypeScript:
- No new connector-specific TS errors.
- Existing pre-existing warnings remain in `ScanPanel.tsx` for unused symbols:
  - `ChevronDown`, `ChevronUp`, `isExpanded`, `toggleExpanded`

## MARKER_147.3_NEXT
Next practical step after server restart:

1. Wire real OAuth callback (custom scheme/deep link) into Tauri.
2. Replace dev auto-complete with true provider auth exchange.
3. Hook ingestion queue consumer into Mycelium workers (actual fetch/parse/chunk/embed).
