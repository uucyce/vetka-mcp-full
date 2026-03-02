# Pulse Terminal Track (Codex in Terminal)

Date: 2026-02-27  
Owner: Terminal Codex  
Status: Active

## Mission
Закрыть implementation-heavy трек без ломки core arbitration:
- UI/DevPanel/операторские контролы;
- durable data plumbing;
- runtime commands и automation around profiling/rebuild/reporting;
- тесты для каждого нового сценария.

## Guardrails
- Не менять policy-ядро scale/key arbitration без согласования.
- Не трогать JEPA scoring формулы в core без marker-а от Architect.
- Любая новая кнопка/команда => интеграционный тест + teletype tag.
- Если есть риск packaged runtime, сразу писать `MARKER_BLOCKER_TERM_*`.

## Marker Protocol
- `MARKER_AUDIT_TERM_*` — проверка текущего поведения перед правкой.
- `MARKER_IMPL_TERM_*` — внедрение.
- `MARKER_TEST_TERM_*` — покрытие тестом + вывод команд.
- `MARKER_BLOCKER_TERM_*` — препятствие/зависимость.

## Terminal Scope
1. UI & controls
- DevPanel controls, Performance mode hygiene, hotkeys.

2. Runtime plumbing
- Tauri commands, file append/rebuild handlers, safe path resolution.

3. Data operations
- dataset fetch/import scripts, corpus/index utilities, report generation wiring.

4. Test coverage
- integration tests for click->event->persist->rebuild;
- regression checks for scripts and file outputs.

## Execution Queue (Terminal)
- [x] `MARKER_AUDIT_TERM_1` Проверить текущие event tags и дубликаты сигналов.
- [x] `MARKER_IMPL_TERM_1` Добавить dedupe защиту для teletype noisy событий.
- [x] `MARKER_TEST_TERM_1` Тест на дубликаты событий в burst-нагрузке.

- [x] `MARKER_AUDIT_TERM_2` Проверить runtime rebuild в dev vs packaged path.
- [x] `MARKER_IMPL_TERM_2` Добавить explicit diagnostics message по источнику пути (dev/app_data/env override).
- [x] `MARKER_TEST_TERM_2` Тест path resolver (3 режима).

- [x] `MARKER_AUDIT_TERM_3` Проверить feedback event schema versioning.
- [x] `MARKER_IMPL_TERM_3` Добавить `schema_version` в feedback event.
- [x] `MARKER_TEST_TERM_3` Тест backward compatibility для старых events.

- [x] `MARKER_AUDIT_TERM_4` Проверить поверхность python-sidecar зависимостей для packaged runtime.
- [x] `MARKER_IMPL_TERM_4` Сформировать migration task-map на native/JS rebuild (без изменения поведения на этом шаге).
- [x] `MARKER_TEST_TERM_4` Добавить acceptance checklist для готовности sidecar-free rebuild.

- [x] `MARKER_AUDIT_B1` Проверить состояние durable spectral telemetry persistence.
- [x] `MARKER_IMPL_B1` Добавить JSONL persistence для spectral telemetry (без правок arbitration).
- [x] `MARKER_TEST_B1` Тесты/прогоны по persistence и schema helpers.

- [x] `MARKER_AUDIT_B2` Проверить отсутствие one-shot quality gate с корректным exit code.
- [x] `MARKER_IMPL_B2` Добавить one-shot quality gate command + md/csv reports.
- [x] `MARKER_TEST_B2` Прогоны gate + тест exit code/report generation.
- [x] `MARKER_AUDIT_B3` Провести аудит ingestion/aggregation `pulse_spectral_telemetry.jsonl`.
- [x] `MARKER_IMPL_B3` Добавить скрипт `ingest_spectral_telemetry.py` + md/csv агрегаты.
- [x] `MARKER_TEST_B3` Добавить тест на агрегацию и прогнать `npm run quality:gate`.

## Report Format (mandatory)
1. Что сделал (по marker IDs).
2. Какие файлы изменил (absolute paths).
3. Какие команды запускал.
4. Что не удалось/риски.
5. Что нужно от Architect.
