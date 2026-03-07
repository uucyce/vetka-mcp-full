MARKER_163.MYCO.VETKA.STRICT_COVERAGE_AUDIT.V1
LAYER: L4
DOMAIN: UI|CHAT|TOOLS|VOICE|AGENTS
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1.md
LAST_VERIFIED: 2026-03-07

# MYCO VETKA Strict Coverage Audit (V1)

## Synopsis
Строгий аудит покрытия phase-163 корпуса: что покрыто доказательно, что остается вне явной документации, какие логические несостыковки были найдены и исправлены.

## Table of Contents
1. Audit method
2. Findings: uncovered modules/windows/modes
3. Logic consistency checks
4. Required closure actions
5. Cross-links
6. Status matrix

## Treatment
Критерий жесткий: если UI surface найден в коде, но не упомянут в phase-163 docs как contract/scenario/gap, считаем это недопокрытием.

## Short Narrative
Базовая архитектура и ключевые пользовательские сценарии уже покрыты, но long-tail поверхностей (особенно MCC внутренних панелей, mention popup, viewer/toolbars) пока не имеют полного contract-описания для MYCO подсказок.

## Full Spec
### Audit method
- Source A: UI surface inventory by filename pattern.
- Source B: phase-163 docs corpus mention scan.
- Source C: status consistency checks (counts, cross-links, markers).

### Findings: Uncovered UI modules (explicit list)
Ниже поверхности, которые есть в `client/src`, но не имели явного contract-level описания в phase-163 narrative layers (до этого strict pass):

- `client/src/components/artifact/viewers/VideoArtifactPlayer.tsx`
- `client/src/components/artifact/viewers/ArtifactViewer.tsx`
- `client/src/components/artifact/FloatingWindow.tsx`
- `client/src/components/artifact/Toolbar.tsx`
- `client/src/components/artifact/ArtifactViewer.tsx`
- `client/src/components/devpanel/ArtifactViewer.tsx`
- `client/src/components/mcc/StreamPanel.tsx`
- `client/src/components/mcc/MiniWindow.tsx`
- `client/src/components/mcc/WorkflowToolbar.tsx`
- `client/src/components/mcc/OnboardingModal.tsx`
- `client/src/components/mcc/DetailPanel.tsx`
- `client/src/components/mcc/OnboardingOverlay.tsx`
- `client/src/components/mcc/TaskEditPopup.tsx`
- `client/src/components/mcc/RolesConfigPanel.tsx`
- `client/src/components/mcc/MCCDetailPanel.tsx`
- `client/src/components/panels/ArchitectChat.tsx`
- `client/src/components/panels/BalancesPanel.tsx`
- `client/src/components/panels/ArtifactViewer.tsx`
- `client/src/components/chat/ChatSidebar.tsx`
- `client/src/components/chat/MentionPopup.tsx`
- `client/src/components/chat/GroupCreatorPanel.tsx`

### Findings: Uncovered/partial modes
- Search contexts `cloud/` and `social/` are visible but unavailable (`client/src/components/search/UnifiedSearchBar.tsx:254`, `client/src/components/search/UnifiedSearchBar.tsx:255`).
- Main VETKA MYCO proactive widget contract still absent (`client/src/App.tsx:246`).
- Full per-control MYCO hint mapping for all 300+ button controls not generated from raw index.

### Logic consistency checks
- Mandatory marker/date header block: present in all deliverable docs.
- Cross-links: normalized to include newly added atlas docs.
- Final report slogan line appears exactly once (`PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07.md:110`).
- UI matrix counts are internally consistent with row statuses (Implemented: 20, Planned: 2, Partial: 0).

### Required closure actions
- P0: Add contract-level docs for uncovered interaction-critical surfaces:
  - `MentionPopup`, `GroupCreatorPanel`, `ChatSidebar`, `WorkflowToolbar`, `MiniWindow`, `VideoArtifactPlayer`, `Artifact Toolbar`.
- P1: Add `TAG` taxonomy expansion for viewer/toolbars/onboarding sub-surfaces.
- P1: Build MYCO hint templates for long-tail controls (at least top-50 by usage).
- P2: Auto-generate doc snippets from `UI_CONTROL_INDEX_RAW_2026-03-07.txt` to avoid manual drift.

## Cross-links
See also:
- [Master Index](./MYCO_VETKA_MASTER_INDEX_V1.md)
- [Windows and Surfaces Atlas](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)
- [Controls and Buttons Atlas](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md)
- [UI Capability Matrix](./MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md)
- [Gap Registry](./MYCO_VETKA_GAP_AND_REMINDERS_V1.md)
- [Recon Report](./PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07.md)

## Status matrix
| Audit area | Status | Evidence |
|---|---|---|
| Core windows/routes | Implemented | `MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md` |
| Core user journeys | Implemented | `MYCO_VETKA_USER_SCENARIOS_ROOT_V1.md` |
| Long-tail sub-surfaces | Partially Implemented | uncovered list above |
| Strict full-surface closure | Planned/Not Implemented | requires additional doc phase |

## Global cross-links
- [MYCO_VETKA_MASTER_INDEX_V1](./MYCO_VETKA_MASTER_INDEX_V1.md)
- [MYCO_VETKA_INFORMATION_ARCHITECTURE_V1](./MYCO_VETKA_INFORMATION_ARCHITECTURE_V1.md)
- [MYCO_VETKA_USER_SCENARIOS_ROOT_V1](./MYCO_VETKA_USER_SCENARIOS_ROOT_V1.md)
- [MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1](./MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md)
- [MYCO_VETKA_CHAT_AND_AGENT_OPERATIONS_V1](./MYCO_VETKA_CHAT_AND_AGENT_OPERATIONS_V1.md)
- [MYCO_VETKA_CONTEXT_MEMORY_STACK_V1](./MYCO_VETKA_CONTEXT_MEMORY_STACK_V1.md)
- [MYCO_VETKA_HELP_HINT_LIBRARY_V1](./MYCO_VETKA_HELP_HINT_LIBRARY_V1.md)
- [MYCO_VETKA_GAP_AND_REMINDERS_V1](./MYCO_VETKA_GAP_AND_REMINDERS_V1.md)
- [MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)
- [MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md)
- [MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1](./MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1.md)
- [MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1](./MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1.md)
- [PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07](./PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07.md)
