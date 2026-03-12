# PHASE 155C — MCP Separation Audit (MCC/VETKA) (2026-03-02)

Marker: `MARKER_155C.RECON.MCP_CODE_SEPARATION_AUDIT.V1`  
Protocol: `RECON + markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`

## 1) Цель аудита
Определить детально:
1. какие части кода должны быть общими (shared core),
2. какие части нужно разделять между MCC и VETKA,
3. как реализовать JEPA-апдейт для Architect без скрытой связки рантаймов.

## 2) Подтвержденный текущий статус (по коду)
1. MCP уже разделен на уровне серверов, но не на уровне репозитория:
   - `.mcp.json` запускает `vetka_mcp_bridge.py` и `mycelium_mcp_server.py` из одного `PYTHONPATH`.
2. API-слой общий:
   - `src/api/routes/__init__.py` регистрирует и `architect_chat_router`, и `mcc_router` в одном FastAPI app.
3. JEPA/packer уже в shared runtime:
   - `src/orchestration/context_packer.py` использует `src/services/mcc_jepa_adapter.py`.
   - `src/services/mcc_jepa_adapter.py` использует runtime module (`src.services.jepa_runtime` по умолчанию).
4. Architect route пока без packer:
   - `src/api/routes/architect_chat_routes.py` строит prompt напрямую и вызывает `call_model_v2`.
5. Bridge shared слой уже существует как паттерн:
   - `src/bridge/shared_tools.py` и `src/bridge/__init__.py`.

## 3) Диагноз по разделению
Текущая архитектура: **dual-MCP на одном монорепо и общем рантайме**.  
Это нормально для скорости разработки, но слабо для автономности MCC как отдельного продукта/деплоя.

Критичный риск: MCC standalone может неявно зависеть от VETKA runtime-структуры и release-cycle.

## 4) Матрица: что shared, что separate

### 4.1 Должно быть `SEPARATE` (product runtime)
1. API routes и transport:
   - `src/api/routes/architect_chat_routes.py`
   - `src/api/routes/mcc_routes.py`
   - product-specific router aggregation (`routes/__init__.py` в каждом продукте)
2. Project/session lifecycle:
   - sandbox/project init/delete/status логика MCC
3. UI state contracts:
   - MCC-specific source mode / drilldown state
4. Product env defaults:
   - URL, порты, флаги runtime и strict-mode policy

### 4.2 Должно быть `SHARED CONTRACT`
1. JEPA context payload schema:
   - `jepa_context`, `jepa_forced`, `provider_mode`, `latency_ms`, `fallback_reason`
2. Trigger semantics:
   - first-call-force, empty-project-skip, hysteresis vocabulary
3. Marker parity contract:
   - единый набор маркеров и DoD для MCC/VETKA

### 4.3 Можно оставить `SHARED IMPLEMENTATION` (через версионируемый core, не через прямой import из соседнего продукта)
1. Алгоритмический packer core (без route-зависимостей)
2. JEPA adapter fallback-chain (`runtime -> embedding -> deterministic`)
3. Runtime health contract (`runtime_health()` payload)
4. Utility-level deterministic vector fallback

## 5) Принцип reuse для MCC
`MCC не должен импортировать VETKA product-runtime файлы напрямую.`  

Разрешенный reuse:
1. общий пакет/вендор-модуль (versioned),
2. копия baseline-файлов в MCC repo с независимым ownership,
3. контрактные тесты на совместимость.

Неразрешенный reuse:
1. `PYTHONPATH`-зависимость MCC на VETKA repo path в проде,
2. прямой import MCC routes из VETKA routes.

## 6) Рекомендуемая целевая структура
1. `shared_core/` (или отдельный пакет):
   - `context_contract.py`
   - `jepa_contract.py`
   - `packer_core.py`
   - `jepa_adapter_core.py`
2. `mcc_runtime/`:
   - MCC routes, project lifecycle, architect bootstrap policy
3. `vetka_runtime/`:
   - VETKA chat/search/UI pipelines

## 7) JEPA для Architect (в контексте разделения)
1. First architect call:
   - если кодовая база непустая -> `force_jepa=true`
   - если проект пустой -> skip JEPA
2. Далее:
   - обычный trigger+hysteresis policy
3. Инъекция:
   - только semantic digest + trace fields по контракту
4. Fallback:
   - architect path не падает при недоступном runtime

## 8) План внедрения разделения (узкий и безопасный)
1. 155C-P0: зафиксировать shared contract doc + parity tests.
2. 155C-P1: внедрить first-call-force/empty-skip в MCC architect runtime.
3. 155C-P2: закрепить fallback chain + runtime-health в MCC.
4. 155C-P3: verify pack (unit + probe + standalone smoke MCC/VETKA отдельно).

## 9) Решение по “общая база vs разделение”
1. Общая кодовая база нужна и разумна для core-алгоритмов/контрактов.
2. Но product runtime (routes, lifecycle, env policy) должен быть разделен.
3. MCC может “брать ту же базу VETKA” только через versioned shared-core слой, не через прямую runtime-связку.

## 10) Артефакты, которые надо синхронизировать в плане 155
1. Этот аудит: `PHASE_155C_MCP_SEPARATION_AUDIT_2026-03-02.md`
2. Recon: `PHASE_155C_JEPA_ARCHITECT_STANDALONE_RECON_2026-03-02.md`
3. Plan: `PHASE_155C_JEPA_ARCHITECT_IMPLEMENTATION_PLAN_2026-03-02.md`
4. Transfer pack: `PHASE_155C_JEPA_ARCHITECT_MCC_TRANSFER_PACK_2026-03-02.md`
