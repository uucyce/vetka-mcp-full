# CODEX IMPL REPORT: Phase 147.4 Connectors Registry Loader

Date: 2026-02-13  
Status: Implemented

## MARKER_147.4_REGISTRY_FILE
Added centralized connector registry:

- `data/connectors_registry.json`
- Includes provider-level static config:
  - `auth_method`
  - `capabilities`
  - `scopes`
  - `redirect_uri`
  - `requires_verification`
  - `rate_limit_model`
  - `token_policy`

## MARKER_147.4_STATE_SERVICE
Refactored state service to merge runtime state + registry config:

- Rewritten: `src/services/connectors_state_service.py`
- Key behavior:
  1. Loads registry from `data/connectors_registry.json`
  2. Auto-fills defaults when registry file is missing/partial
  3. Persists only mutable runtime fields in `data/connectors_state.json`
  4. Returns merged output via `list()`
  5. Exposes `get_registry()` for pure registry API

## MARKER_147.4_API
Extended connectors routes:

- Updated response model in `src/api/routes/connectors_routes.py`:
  - `requires_verification`
  - `rate_limit_model`
  - `token_policy`
- Added endpoint:
  - `GET /api/connectors/registry`

## MARKER_147.4_SCANPANEL
Updated ScanPanel connector typing + badges:

- `client/src/components/scanner/ScanPanel.tsx`
  - extended `ConnectorProvider` fields
  - shows `review required` badge for providers with `requires_verification`
- `client/src/components/scanner/ScanPanel.css`
  - styles for `connector-policy`, `connector-refresh`, `connector-capabilities`

## MARKER_147.4_CHECKS
Verification:

1. Python compile:
- `py_compile` on connectors services/routes: OK

2. TypeScript:
- no new connector-specific failures
- old existing warnings in `ScanPanel.tsx` remain (unused symbols)

