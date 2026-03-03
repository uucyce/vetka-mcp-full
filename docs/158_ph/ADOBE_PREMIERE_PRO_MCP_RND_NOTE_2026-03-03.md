# Adobe_Premiere_Pro_MCP R&D Note (Narrow Reuse for VETKA)
**Date:** 2026-03-03  
**Source repo:** `https://github.com/hetpatel-11/Adobe_Premiere_Pro_MCP`  
**Local audit snapshot:** `/tmp/adobe_mcp_MVsNAL/repo`

## Scope
Цель анализа: определить, что можно безопасно переиспользовать в VETKA как стабильные наработки, без попытки внедрять весь проект целиком.

## What is useful for VETKA
1. Bridge pattern `MCP -> Node server -> CEP panel -> ExtendScript`.
2. Файловый transport через temp-dir и polling (рабочий pragmatic fallback when no direct host bridge).
3. ExtendScript helper-идея (sequence/clip lookup, time conversion wrappers).
4. Список типовых поломок из `KNOWN_ISSUES.md` как готовый чеклист quality-gates.

## What not to import as-is
1. Полный набор инструментов (`97 tools`) как готовую production гарантию.
2. Широкую бизнес-логику tool-слоя из `src/tools/index.ts` без полной ревизии.
3. Предположение, что UXP закрывает сценарии ExtendScript исполнения (в репо явно опора на CEP для ExtendScript).

## Evidence from source
1. Архитектура моста и workflow описаны в `README.md` (`How it works`, bridge stages, helper prepend, CEP evalScript path).
2. Установка/операционный контур через CEP и temp-dir в `QUICKSTART.md`.
3. Риски/дефекты инструментов документированы в `KNOWN_ISSUES.md`:
   - missing `return` in ExtendScript blocks,
   - scope issues in template literals,
   - необходимость системного аудита всех tool scripts.
4. Структура кода компактная и понятная:
   - `src/bridge/index.ts`
   - `src/tools/index.ts`
   - `src/utils/security.ts`

## Recommended narrow extraction plan for VETKA
1. Reuse pattern only:
   - transport contract (`command file` / `result file`),
   - bridge lifecycle states (`connected`, `ready`, `timeout`, `error`).
2. Build VETKA-specific helper layer:
   - `findSequence`, `findTrack`, `findClipByTime`, `timecode<->seconds`.
3. Add mandatory script quality gates before execution:
   - explicit `return` requirement,
   - no unresolved template vars,
   - path sanitization + allowed roots.
4. Start from critical tools only (not 97):
   - list active sequence,
   - list tracks/clips,
   - add marker,
   - import clip to timeline,
   - export XML/FCPXML trigger.

## Integration boundary with current VETKA
1. Keep existing JSON->Premiere XML lane as primary interchange.
2. Treat MCP Premiere bridge as optional live-control lane.
3. Use one adapter boundary in VETKA:
   - `PremiereAdapter` interface with two implementations:
     - `xml_interchange_adapter` (already present),
     - `mcp_live_bridge_adapter` (future opt-in).

## Decision
Репозиторий полезен как reference architecture + anti-pattern catalog.  
Для VETKA рационально брать только инфраструктурный и quality-gate слой, не переносить целиком tool-suite.
