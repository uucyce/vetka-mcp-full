# CODEX RECON — Phase 151 Wave 5 (Onboarding + Polish)

Date: 2026-02-15
Scope: frontend only, narrow implementation slice

## MARKER_151.13_RECON
Current `client/src/components/panels/PipelineStats.tsx` still uses legacy-heavy layout (recharts + broad mixed metrics), not focused on per-agent weak-link cards.

Decision:
- Rewrite to Stats v2 with per-agent role cards from `task.stats.agent_stats`.
- Keep compact mode summary for MCC detail panel.

## MARKER_151.15_RECON
No onboarding hook/state machine in current codebase. Header controls have no onboarding target markers.

Decision:
- Add `useOnboarding` hook with localStorage persistence.
- Add `OnboardingOverlay` component.
- Integrate into `MyceliumCommandCenter` and target header controls via `data-onboarding` markers.

## MARKER_151.16_RECON
Header tooltips mostly static `title` attributes and always shown.

Decision:
- Add lightweight hover-limiter utility (`3 views then hidden`) for key header controls.

## MARKER_151.17_RECON
No centralized Nolan tokens file imported globally.

Decision:
- Add `client/src/styles/tokens.css` and import in `main.tsx`.
- Apply tokens in most visible new/edited controls only.

## MARKER_151.18_RECON
Playground/workflow full mapping needs broader backend + data model work.

Decision for this pass (safe minimum):
- On Execute from MCC header, if no playground exists, auto-create one via existing API.
- Keep workflow mapping out of this pass to avoid speculative backend coupling.
