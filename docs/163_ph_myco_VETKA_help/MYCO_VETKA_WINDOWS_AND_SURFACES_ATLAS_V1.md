MARKER_163.MYCO.VETKA.WINDOWS_SURFACES_ATLAS.V1
LAYER: L2
DOMAIN: UI|CHAT|TOOLS|AGENTS
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md
LAST_VERIFIED: 2026-03-07

# MYCO VETKA Windows and Surfaces Atlas (V1)

## Synopsis
Полный реестр окон/полуокон VETKA: route-level surfaces, native Tauri windows, embedded panels, modals/overlays, и события переключения между ними.

## Table of Contents
1. L0 route windows
2. L1 native Tauri windows
3. L2 embedded panels and half-windows
4. L3 modal/overlay surfaces
5. Cross-links
6. Status matrix

## Treatment
Этот atlas фиксирует UI-среду, в которой MYCO должен давать прицельные подсказки на основе текущего окна и текущей панели.

## Short Narrative
Пользователь живет не в одной странице, а в стекe поверхностей: `App` + чаты + артефакты + scanner + detached windows + web shell. Если MYCO знает активную поверхность, он может давать короткий next-best-step без шумов.

## Full Spec
### L0 Route windows (`TAG:UI.ROUTE.WINDOW.*`)
| Surface | Trigger | Evidence | Status |
|---|---|---|---|
| Main VETKA app (`/`) | default route | `client/src/main.tsx:25`, `client/src/main.tsx:40` | Implemented |
| MYCELIUM standalone (`/mycelium`) | route switch | `client/src/main.tsx:28`, `client/src/MyceliumStandalone.tsx:11` | Implemented |
| Web Shell (`/web-shell`) | route switch | `client/src/main.tsx:31`, `client/src/WebShellStandalone.tsx:81` | Implemented |
| Detached artifact (`/artifact-window`) | route switch | `client/src/main.tsx:37`, `client/src/ArtifactStandalone.tsx:41` | Implemented |
| Detached media (`/artifact-media`) | route switch | `client/src/main.tsx:34`, `client/src/ArtifactMediaStandalone.tsx:39` | Implemented |

### L1 Native Tauri windows (`TAG:UI.TAURI.WINDOW.*`)
| Native window | Open/close path | Evidence | Status |
|---|---|---|---|
| `main` | static config | `client/src-tauri/tauri.conf.json:16` | Implemented |
| `mycelium` | static config + `open_mycelium` | `client/src-tauri/tauri.conf.json:29`, `client/src-tauri/src/main.rs:17` | Implemented |
| `artifact-main` detached | `open_artifact_window` command | `client/src-tauri/src/main.rs:66`, `client/src-tauri/src/commands.rs:260` | Implemented |
| `artifact-media` detached | `open_artifact_media_window` command | `client/src-tauri/src/main.rs:67`, `client/src-tauri/src/commands.rs:195` | Implemented |
| direct web window | `open_direct_web_window` command | `client/src-tauri/src/main.rs:71` | Implemented |

### L2 Embedded panels and half-windows (`TAG:UI.PANEL.*`)
| Panel / half-window | Where shown | Evidence | Status |
|---|---|---|---|
| Chat panel | Main app overlay side panel | `client/src/App.tsx:1126`, `client/src/components/chat/ChatPanel.tsx:2455` | Implemented |
| Left chat history panel | `leftPanel === 'history'` | `client/src/components/chat/ChatPanel.tsx:2398` | Implemented |
| Left phonebook panel (`ModelDirectory`) | `leftPanel === 'models'` | `client/src/components/chat/ChatPanel.tsx:2407`, `client/src/components/ModelDirectory.tsx:2` | Implemented |
| ArtifactWindow (embedded floating wrapper) | App surface | `client/src/App.tsx:1029`, `client/src/components/artifact/ArtifactWindow.tsx:54` | Implemented |
| Unified Search bar surface | top strip in App | `client/src/App.tsx:1063`, `client/src/components/search/UnifiedSearchBar.tsx:1` | Implemented |
| Scanner panel | inside chat work surface | `client/src/components/scanner/ScanPanel.tsx:1116` | Implemented |
| DevPanel/MCC panel | standalone mycelium | `client/src/MyceliumStandalone.tsx:19`, `client/src/components/panels/DevPanel.tsx:1` | Implemented |

### L3 Modal and overlay surfaces (`TAG:UI.MODAL.OVERLAY.*`)
| Modal/overlay | Purpose | Evidence | Status |
|---|---|---|---|
| Node context menu | tree mode + cleanup actions | `client/src/App.tsx:1253`, `client/src/App.tsx:1278` | Implemented |
| Folder cleanup confirm modal | index-only cleanup confirmation | `client/src/App.tsx:1433`, `client/src/App.tsx:1482` | Implemented |
| Connector auth modal | OAuth/API key/manual link connect | `client/src/components/scanner/ScanPanel.tsx:1443`, `client/src/components/scanner/ScanPanel.tsx:1455` | Implemented |
| Connector tree selection modal | choose cloud files/folders before scan | `client/src/components/scanner/ScanPanel.tsx:1538`, `client/src/components/scanner/ScanPanel.tsx:1562` | Implemented |
| WebShell save modal (2-step) | save web page into VETKA | `client/src/WebShellStandalone.tsx:591`, `client/src/WebShellStandalone.tsx:596` | Implemented |
| Drop overlay | file drop routing | `client/src/components/DropZoneRouter.tsx:291` | Implemented |

### Event and state bridge for MYCO surface awareness
- Window and panel switching events are actively dispatched/listened in `App` and socket hook.
- Evidence: `client/src/App.tsx:769`, `client/src/App.tsx:829`, `client/src/hooks/useSocket.ts:1597`, `client/src/hooks/useSocket.ts:1948`.

### Raw exhaustive indices
- Full surface grep dump: `docs/163_ph_myco_VETKA_help/UI_SURFACE_INDEX_RAW_2026-03-07.txt`.
- Full control grep dump: `docs/163_ph_myco_VETKA_help/UI_CONTROL_INDEX_RAW_2026-03-07.txt`.

## Cross-links
See also:
- [Master Index](./MYCO_VETKA_MASTER_INDEX_V1.md)
- [Information Architecture](./MYCO_VETKA_INFORMATION_ARCHITECTURE_V1.md)
- [User Scenarios Root](./MYCO_VETKA_USER_SCENARIOS_ROOT_V1.md)
- [UI Capability Matrix](./MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md)
- [Controls Atlas](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md)
- [Long-tail Surfaces Scenarios](./MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1.md)
- [Button Hint Catalog](./MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md)
- [Search/Phonebook Guide](./MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1.md)
- [Cloud Social Search Contract](./MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1.md)
- [Strict Coverage Audit](./MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1.md)
- [Recon Report](./PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07.md)

## Status matrix
| Scope | Status | Evidence |
|---|---|---|
| Route/window atlas | Implemented | this file + `client/src/main.tsx:25` |
| Native window command mapping | Implemented | `client/src-tauri/src/main.rs:55` |
| MYCO-aware panel activation in VETKA main | Partially Implemented | events exist, MYCO widget missing in `client/src/App.tsx` |
