# CODEX PLAN — Phase 150: File Search OS Index + Hybrid

Дата: 2026-02-15
Контекст: `file/` режим в VETKA, кроссплатформенный быстрый поиск + интеграция в существующий pipeline.

## Executive Summary
- GO на Phase A (macOS-first): `mdfind` + `rg` + существующий VETKA API контракт.
- GO на Hybrid (Phase B): `semantic` (Qdrant) + `keyword/name` + RRF rerank.
- GO на dedup detect-only (Phase C): `fdupes` как optional scanner, без удаления по умолчанию.
- `fzf` — optional helper, не блокирующий основной UI/REST путь.

## Маркеры под имплементацию

### MARKER_150.FILE_API_SURFACE
Цель: добавить явный API слой для file-поиска.
- Новый endpoint: `POST /api/search/file`
- Новый endpoint: `GET /api/search/file/capabilities`
- Новый endpoint: `POST /api/files/duplicates` (scan/report, delete пока disabled)
- Контракт ответа: единый с `unified_search` (`results`, `total`, `took_ms`, `mode`, `source`).

### MARKER_150.FILE_OS_INDEX_ADAPTER
Цель: подключить OS-native индекс с fallback.
- macOS: `mdfind` как primary filename/content candidate provider.
- Linux: `plocate/locate` если доступно, иначе `fd`.
- Windows: Windows Search/Everything adapter (placeholder с fallback).
- Общий fallback: `fd` + ограниченный `os.walk`.
- Реализация через сервис-адаптер: `src/search/file_os_index_adapter.py`.

### MARKER_150.FILE_CONTENT_GREP
Цель: быстрый content search по локальным файлам.
- `rg --json` как основной content engine.
- Ограничения: размер файла, бинарные типы, ignore policy.
- Сниппеты для UI из первых матчей.
- Реализация: `src/search/file_content_search.py`.

### MARKER_150.FILE_HYBRID_RRF
Цель: объединить name/content/semantic в один ранжированный поток.
- Режимы: `name`, `content`, `semantic`, `hybrid`.
- Hybrid: RRF (`k=60`) + базовый MMR diversity на top-N.
- Переиспользовать существующий `HybridSearchService` и фильтрацию по roots.
- Реализация: `src/search/file_search_service.py`.

### MARKER_150.FILE_VIEWPORT_ROOT_POLICY
Цель: file/ поиск учитывает viewport context как корневые области поиска.
- Приоритет roots:
  1. pinned file/folder paths
  2. nearest viewport file/folder paths
  3. selected node path
  4. project root fallback
- Нормализация: file -> parent folder.
- Удаление шумных virtual/chat путей.
- Реализация в frontend query builder + backend sanitizer.

### MARKER_150.FILE_CAPABILITIES_DYNAMIC_UI
Цель: динамически включать/выключать кнопки режимов в `file/`.
- Отдавать в `capabilities`:
  - `supports_name`, `supports_content`, `supports_semantic`, `supports_hybrid`
  - `supports_fzf`, `supports_duplicates_scan`
  - `active_provider` (`mdfind`, `fd`, `locate`, ...)
- UI: скрывать недоступные кнопки, не показывать broken mode.

### MARKER_150.FILE_DUPLICATES_SAFE_FLOW
Цель: безопасный dedup без разрушения данных.
- Phase C: только scan/report clusters.
- Никакого auto-delete.
- Возможный delete позже: только explicit confirm flow.
- В ответе: group_id, paths, size bytes, hash.

### MARKER_150.FILE_QDRANT_INDEX_SYNC
Цель: сохранить совместимость с текущим triple-write и semantic index.
- Любой новый/обновлённый файл после save/scan должен попадать в существующий watcher pipeline.
- Проверка в логах: `TripleWrite`, `qdrant: True`.
- Не создавать параллельный индексный контур.

### MARKER_150.FILE_TESTS
Цель: закрыть риски регрессии до merge.
- Unit:
  - root policy normalizer
  - os-index adapter fallback selection
  - RRF merge correctness
- Integration:
  - `/api/search/file` modes
  - capabilities response by platform/tools
- E2E:
  - `file/` query -> open file -> camera focus
  - no regression for `vetka/` and `web/`

## Фазный план

### Phase A (MVP, 1-2 дня)
- `MARKER_150.FILE_API_SURFACE`
- `MARKER_150.FILE_OS_INDEX_ADAPTER` (macOS + generic fallback)
- `MARKER_150.FILE_CONTENT_GREP`
- `MARKER_150.FILE_VIEWPORT_ROOT_POLICY`
- `MARKER_150.FILE_CAPABILITIES_DYNAMIC_UI` (минимум)

Критерий готовности:
- `file/` поиск стабильно работает, даёт релевантные локальные файлы и сниппеты.
- Не ломает `web/` и `vetka/`.

### Phase B (Hybrid/semantic)
- `MARKER_150.FILE_HYBRID_RRF`
- `MARKER_150.FILE_QDRANT_INDEX_SYNC`

Критерий готовности:
- Hybrid заметно лучше `name`/`content` на коротких запросах.

### Phase C (dedup + optional tools)
- `MARKER_150.FILE_DUPLICATES_SAFE_FLOW`
- `MARKER_150.FILE_CAPABILITIES_DYNAMIC_UI` (full)
- `MARKER_150.FILE_TESTS` (expanded)

## GO / NO-GO
- GO: macOS-first внедрение прямо сейчас.
- GO: `fdupes` detect-only, `fzf` optional.
- NO-GO: destructive dedup/delete в дефолтном режиме.
- NO-GO: отдельный индексный контур в обход watcher+Qdrant.

## Что имплементировать следующим шагом (конкретно)
1. В backend добавить `POST /api/search/file` + service-слой с mode dispatch.
2. Подключить `mdfind` provider (если доступен) и fallback `fd/rg`.
3. В UI `file/` переключить modes по `capabilities`.
4. Добавить базовые тесты для root policy + mode dispatch.
