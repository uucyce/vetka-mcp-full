# MARKER_157_1_CONTEXT_PACKER_PROBE_TOOL_2026-03-01

## Что сделано
- Добавлен probe-инструмент для локальных замеров trigger/hysteresis:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/context_packer_probe.py`
- Усилен `ContextPacker`:
  - hysteresis (`ON/OFF` streak thresholds),
  - trace-поля для raw/effective trigger,
  - latency метрики `pack_latency_ms`, `jepa_latency_ms`,
  - in-memory recent stats API `get_recent_stats(limit=...)`.

## Быстрый запуск
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python scripts/context_packer_probe.py --synthetic --runs 50
python scripts/context_packer_probe.py --synthetic --runs 120 --output /tmp/phase157_probe.jsonl
```

## Что смотреть в выводе
- `jepa_mode_ratio`: доля реальных JEPA включений
- `pack_latency_ms_p95`: p95 общего pack latency
- `jepa_latency_ms_p95`: p95 latency JEPA-ветки
- по строкам:
  - `jepa_trigger_raw` (сырой триггер),
  - `jepa_trigger` (после hysteresis),
  - `hysteresis_on_streak` / `hysteresis_off_streak`.

## Тюнинг без хардкода
Использовать env-переменные:
- `VETKA_CONTEXT_PACKER_HYSTERESIS_ON` (default: 3)
- `VETKA_CONTEXT_PACKER_HYSTERESIS_OFF` (default: 2)
- `VETKA_CONTEXT_PACKER_DOCS_THRESHOLD`
- `VETKA_CONTEXT_PACKER_TOKEN_PRESSURE`
- `VETKA_CONTEXT_PACKER_ENTROPY_THRESHOLD`
- `VETKA_CONTEXT_PACKER_MODALITY_THRESHOLD`

Только после стабильных реальных замеров из вашей нагрузки масштабировать JEPA-tool на агентов.
