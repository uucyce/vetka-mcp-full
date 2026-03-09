# VETKA_CUT_PHASE_170_VISION_SPEC_V1
**Created:** 2026-03-09  
**Status:** draft-for-execution  
**Scope:** `VETKA CUT` standalone sandbox + future `edit_mode` reintegration

## CHANGELOG_2026-03-09_Codex
1. Зафиксировано решение запускать `VETKA CUT` в отдельной песочнице на копии `VETKA Core`.
2. Зафиксировано, что `VETKA CUT` сначала живет как standalone product/runtime, а затем может стать встроенным `edit_mode`.
3. Подтверждено, что главным УТП CUT является не timeline сам по себе, а монтаж поверх `VETKA` scan/search/memory/import core.
4. Зафиксирована MCP topology: `CUT MCP` + тяжелый media worker / sub-MCP lane.
5. Зафиксирована стратегия синхронизации sandbox с upstream `VETKA Core`.

---

## 1) Product Intent
`VETKA CUT` = AI-native montage system on top of `VETKA Core`.

Не цель:
1. Сделать еще один video player.
2. Сделать декоративный timeline без intelligence.
3. Тащить нестабильный media runtime прямо в основной продукт раньше времени.

Цель:
1. Поднять standalone монтажную систему быстрее основной VETKA.
2. Использовать существующее ядро `scan/search/import/memory/context` как основу монтажа.
3. Позже вернуть CUT обратно в VETKA как стабильный `edit_mode`.

---

## 2) Naming
### 2.1 Brand
- `VETKA CUT`

### 2.2 Preferred architectural expansion
- `CUT = Contextual Unified Timeline`

### 2.3 Secondary product line / manifesto
- `Cinematic Understanding of Time`

Решение:
1. Во внешнем продукте использовать `VETKA CUT`.
2. В архитектурных документах использовать `Contextual Unified Timeline`.
3. В UI/tagline допустимо использовать `AI Montage Engine` или `Cinematic Understanding of Time`.

---

## 3) Why sandbox first
1. Нестабильный монтажный runtime не должен крашить основную VETKA.
2. Heavy media processing не должен шуметь в текущем рабочем контуре команды.
3. Песочница изолирует коммиты, миграции и runtime-эксперименты других агентов.
4. Standalone CUT дает ранний пользовательский feedback до полной интеграции в основной продукт.
5. Копия `VETKA Core` внутри sandbox не запрещена: это уже практикуется в `MYCELIUM` workflow.

---

## 4) Core thesis
Сила `VETKA CUT` не в том, что он умеет резать клипы, а в том, что он режет клипы поверх:
1. `watcher/import/index` pipeline,
2. `ExtractorRegistry` + multimodal extraction,
3. `media_chunks_v1` / `vetka_montage_sheet_v1`,
4. semantic/vector search,
5. `CAM` / `ENGRAM` / `STM` / `MGC` context memory,
6. `JEPA` / `PULSE` / optional media enrichments,
7. `MCP` orchestration and async job runtime.

Именно это делает CUT потенциально отдельным продуктом, а не просто UI-режимом.

---

## 5) Operating model
### 5.1 Phase 1: standalone
1. `VETKA CUT` живет как отдельная песочница.
2. Поднимает собственные MCP/runtime процессы.
3. Имеет собственные очереди, временное хранение, worker lanes и telemetry.
4. Использует mirror-copy `VETKA Core` как базовый слой.

### 5.2 Phase 2: synchronized fork
1. CUT периодически подтягивает изменения из upstream `VETKA Core`.
2. Общие контракты и ядро синхронизируются автоматически или semi-automatically.
3. CUT-specific код остается изолированным в своих namespaces/modules.

### 5.3 Phase 3: reintegration
1. Когда CUT стабилен, он может быть подключен обратно как `VETKA edit mode`.
2. Интеграция идет через те же contracts/MCP boundaries.
3. Основная VETKA не обязана принимать незрелый runtime до готовности.

---

## 6) Top-level system shape
```text
VETKA Core Mirror
├─ import / watcher / scan
├─ extractor registry / multimodal contracts
├─ qdrant / triple-write / media chunks
├─ CAM / ENGRAM / STM / MGC / ELISION
└─ shared MCP primitives

VETKA CUT Runtime
├─ CUT MCP (orchestrator)
├─ Media Worker MCP / sub-MCP
├─ timeline state + montage sheet
├─ semantic links / scene graph / assists
└─ standalone CUT UI
```

---

## 7) Boundaries
### 7.1 Shared with Core
1. `media_chunks_v1`
2. `vetka_montage_sheet_v1`
3. media import/extraction contracts
4. memory/context interfaces
5. async job envelope principles

### 7.2 CUT-owned
1. montage runtime orchestration
2. timeline engine and edit state
3. scene assembly logic
4. take selection / recut flows
5. edit UI / playback control / editorial overlays
6. export workflows and future live NLE bridges

---

## 8) Non-goals for Phase 170
1. Не делать сразу полный replacement Premiere/Resolve.
2. Не переносить весь CUT обратно в основной VETKA на раннем этапе.
3. Не смешивать unstable worker code с production routes основного продукта.
4. Не пытаться сразу завершить все advanced layers (`multicam Z`, deep music auto-edit, full node compositor).

---

## 9) Success criteria
1. CUT поднимается отдельно и не ломает основной VETKA runtime.
2. Sandbox использует реальное VETKA core behavior, а не фейковый mock editor.
3. CUT ingest/analyze/timeline loop работает на реальных медиа-папках.
4. Upstream-sync strategy не дает песочнице окончательно оторваться от ядра.
5. Реинтеграция обратно в VETKA остается технически возможной без полного rewrite.
