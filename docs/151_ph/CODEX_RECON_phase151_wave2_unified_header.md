# CODEX RECON — Phase 151 Wave 2 (Unified Header)

Date: 2026-02-15
Scope: frontend only (`client/src/components/mcc/*`)
Protocol: RECON -> REPORT -> IMPL (narrow)

## MARKER_151.5_RECON_HEADER_CURRENT
Current header in `client/src/components/mcc/MyceliumCommandCenter.tsx` still uses legacy layout:
- Left: `MCC`, `PresetDropdown`, `LIVE/OFF`
- Right: `WatcherMicroStatus`, `HeartbeatChip`, `PlaygroundBadge`, stats, stream toggle, panel toggles

Gap vs brief:
- `WatcherMicroStatus` must be removed from header
- `PlaygroundBadge` must be replaced by `SandboxDropdown`
- `KeyDropdown` is missing
- `Execute` still lives in `WorkflowToolbar.tsx` instead of header
- stream toggle button still present (brief requires removal)

## MARKER_151.5_RECON_SANDBOX
`client/src/components/mcc/SandboxDropdown.tsx` already exists and is usable:
- Fetches list from `GET /api/debug/playground`
- Creates sandbox via `POST /api/debug/playground/create`
- Destroys sandbox via `DELETE /api/debug/playground/{id}`

Conclusion: no backend change required for sandbox control.

## MARKER_151.6_RECON_EXECUTE
`client/src/components/mcc/WorkflowToolbar.tsx` currently contains `handleExecute` and renders `[▶ Execute]`.

Gap vs brief:
- Execute button should move to MCC header
- Execute button should be removed from toolbar

## MARKER_151.7_RECON_STREAM
`MyceliumCommandCenter.tsx` has manual `showStream` toggle button in header and conditional render `{showStream && <StreamPanel .../>}`.

Target per brief:
- remove manual stream toggle button
- auto-show stream when there are running tasks
- auto-hide when idle

## MARKER_151.5_RECON_KEYS
No `KeyDropdown` component exists in mcc folder.
Available data sources:
- `GET /api/debug/usage/balances` already used by `BalancesPanel.tsx`
- selected key storage available in `client/src/store/useStore.ts`:
  - `selectedKey`
  - `setSelectedKey`

Conclusion: implement `KeyDropdown` as a small standalone frontend component.

## Narrow implementation plan
1. Add `client/src/components/mcc/KeyDropdown.tsx` using balances API + `useStore` selection.
2. Rewrite MCC header row in `MyceliumCommandCenter.tsx` to unified bar:
   `PresetDropdown + SandboxDropdown + HeartbeatChip + KeyDropdown + LIVE + stats + Execute + panel toggles`.
3. Move execute logic to MCC (single handler), pass `onExecute` to toolbar only if needed, remove toolbar execute button.
4. Remove `WatcherMicroStatus`, `PlaygroundBadge`, and stream toggle button from header.
5. Add auto stream visibility rule based on running tasks (`summary.by_status.running` or `stats.runningTasks`).
6. Verify with focused TypeScript check/build slice.

## Risk notes
- Workspace has unrelated pre-existing changes and TS issues; validation will be scoped to touched files.
- No changes to camera/file indexing logic in this wave.
