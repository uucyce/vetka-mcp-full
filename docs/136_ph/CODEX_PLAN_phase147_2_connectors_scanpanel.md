# CODEX PLAN: Phase 147.2 Connectors in ScanPanel

Date: 2026-02-13  
Scope: Cloud/Social onboarding and scan actions from chat ScanPanel

## MARKER_147.2_RECON
- Existing `ScanPanel` already has source tabs: `local/cloud/browser/social`.
- `cloud/social` currently hardcoded as "Coming soon".
- Backend has no `/api/connectors/*` contract yet.
- Main FastAPI app registers routes through `src/api/routes/__init__.py`.

## MARKER_147.2_DECISION
- Implement **minimal production-safe connector layer** now:
  - no password storage in VETKA DB;
  - no fake OAuth complexity in UI;
  - persistent connector state in `data/connectors_state.json`;
  - explicit connect/scan/disconnect actions.
- Keep architecture ready for later OAuth/keychain integration.

## MARKER_147.2_API_CONTRACT
- `GET /api/connectors/status?source=cloud|social`
  - returns providers list with `connected`, `account_label`, `last_sync_at`, `last_scan_count`.
- `POST /api/connectors/{provider}/connect`
  - marks provider connected, stores metadata only.
- `POST /api/connectors/{provider}/scan`
  - triggers connector scan stub (returns count + timestamp), updates provider state.
- `POST /api/connectors/{provider}/disconnect`
  - disconnect provider and clear account metadata.

## MARKER_147.2_SCANPANEL_UI
- Replace "Coming soon" for `cloud/social` with actionable provider cards:
  - provider name + status chip;
  - buttons: `Connect`, `Scan`, `Disconnect` (contextual by status);
  - loading state per provider and source.
- Preserve VETKA black style and compact layout.

## MARKER_147.2_STATE_MODEL
- New backend state file: `data/connectors_state.json`
- Per provider:
  - `id`, `source`, `display_name`, `connected`
  - `account_label`, `last_sync_at`, `last_scan_count`, `updated_at`

## MARKER_147.2_RESEARCH_REQUIRED
- Required before OAuth/keychain wave:
  1. Final provider list for MVP (`google_drive`, `dropbox`, `gmail`, `github`, `x`).
  2. Native secure token storage strategy (Keychain/Credential Manager/libsecret).
  3. Sync policy and ingestion boundaries (what exactly is scanned).

## MARKER_147.2_IMPL_SEQUENCE
1. Add backend connector state service.
2. Add `connectors_routes.py` and register router.
3. Replace `ScanPanel` cloud/social placeholder with live connector cards.
4. Add style rules in `ScanPanel.css`.
5. Run quick compile checks and validate route registration.

