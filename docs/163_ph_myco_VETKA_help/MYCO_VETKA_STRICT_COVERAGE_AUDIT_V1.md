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
Core path покрыт. Second-pass закрыл long-tail surfaces и button catalog. Остаются runtime gap-ы: main VETKA MYCO widget, cloud/social execution, non-button интерактивы.

## Full Spec
### Audit method
- Source A: UI surface inventory by filename pattern.
- Source B: phase-163 docs corpus mention scan.
- Source C: status consistency checks (counts, cross-links, markers).

### Findings: Previously uncovered UI modules (closed in this pass)
Ниже поверхности были непокрыты и закрыты этим pass через long-tail scenario contracts:

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

Closure evidence:
- `docs/163_ph_myco_VETKA_help/MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1.md`

### Findings: Remaining uncovered/partial modes
- Search contexts `cloud/` and `social/` are visible but unavailable (`client/src/components/search/UnifiedSearchBar.tsx:254`, `client/src/components/search/UnifiedSearchBar.tsx:255`).
- Main VETKA MYCO proactive widget contract still absent (`client/src/App.tsx:246`).
- Non-button clickable interactions still lack dedicated hint catalog (button catalog is now covered).

Closure evidence for button layer:
- `docs/163_ph_myco_VETKA_help/MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md` (336 rows).

### Logic consistency checks
- Mandatory marker/date header block: present in all deliverable docs.
- Cross-links: normalized to include newly added atlas docs.
- Final report slogan line appears exactly once (`PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07.md:110`).
- UI matrix counts are internally consistent with row statuses (Implemented: 20, Planned: 2, Partial: 0).

### Required closure actions
- P0: Bind main VETKA surface to MYCO quick payload/widget contract.
- P1: Implement cloud/social execution branches or hide unavailable contexts.
- P1: Add non-button interactive hint catalog (`onClick` div/span/custom controls).
- P2: Auto-sync catalog generation in CI to prevent drift.

## Cross-links
See also:
- [Master Index](./MYCO_VETKA_MASTER_INDEX_V1.md)
- [Windows and Surfaces Atlas](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)
- [Controls and Buttons Atlas](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md)
- [Button Hint Catalog](./MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md)
- [Long-tail Surfaces Scenarios](./MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1.md)
- [UI Capability Matrix](./MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md)
- [Gap Registry](./MYCO_VETKA_GAP_AND_REMINDERS_V1.md)
- [Recon Report](./PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07.md)

## Status matrix
| Audit area | Status | Evidence |
|---|---|---|
| Core windows/routes | Implemented | `MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md` |
| Core user journeys | Implemented | `MYCO_VETKA_USER_SCENARIOS_ROOT_V1.md` |
| Long-tail sub-surfaces | Implemented | `MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1.md` |
| Button-level hint layer | Implemented | `MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md` |
| Strict full-surface closure | Partially Implemented | non-button + runtime gaps remain |

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
- [MYCO_VETKA_BUTTON_HINT_CATALOG_V1](./MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md)
- [MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1](./MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1.md)
- [MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1](./MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1.md)
- [MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1](./MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1.md)
- [MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1](./MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1.md)
- [PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07](./PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07.md)
