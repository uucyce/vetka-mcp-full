# Pulse UI v3 Track (Agent C)

Date: 2026-02-28  
Owner: UI Subagent (Agent C)  
Status: Active

## Mission
Собрать performance-first UI v3 без raw video:
- hand-only визуал,
- note matrix, синхронный Camelot wheel,
- минимальный когнитивный шум в перформанс-режиме.

## Guardrails
- Не менять audio/key/scale/JEPA backend контракты.
- Любая UI правка должна иметь smoke/logic тест.
- Все новые маркеры писать в `PULSE_SHARED_CHECKLIST.md`.

## Marker Protocol
- `MARKER_AUDIT_C*`
- `MARKER_IMPL_C*`
- `MARKER_TEST_C*`
- `MARKER_BLOCKER_C*`

## Current Closed Markers
- [x] `MARKER_AUDIT_C1` inspect existing performance view split/fallback.
- [x] `MARKER_IMPL_C1` UI v3 mode + v2 fallback plumbing.
- [x] `MARKER_TEST_C1` performance view mode tests.
- [x] `MARKER_AUDIT_C2` inspect color/note visualization gaps.
- [x] `MARKER_IMPL_C2` add VerticalNoteMatrix + active note highlighting.
- [x] `MARKER_TEST_C2` matrix rendering/mapping tests.

## Next Queue
- [ ] `MARKER_AUDIT_C3` audit hand-overlay clarity on dark/bright backgrounds.
- [ ] `MARKER_IMPL_C3` improve landmark contrast and active-hand emphasis.
- [ ] `MARKER_TEST_C3` screenshot/smoke assertions for visibility.
- [ ] `MARKER_AUDIT_C4` audit mobile-like window layout breakpoints.
- [ ] `MARKER_IMPL_C4` adaptive sizing for wheel + matrix + controls.
- [ ] `MARKER_TEST_C4` responsive smoke tests.

## Report Format (mandatory)
1. Marker IDs done.
2. Files changed (absolute paths).
3. Commands run.
4. Risks/known gaps.
5. Questions for Architect.

