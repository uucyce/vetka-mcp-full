# MARKER_157_1_RUNTIME_ENV_CANON_2026-03-01

## Что зафиксировано
- Введен единый runtime-профиль для ContextPacker/JEPA:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/config/runtime.env`
- `run.sh` теперь централизованно подгружает:
  1. `.env` (если есть),
  2. `config/runtime.env` (канон Phase 157.1),
  3. и выставляет fallback defaults через `export ...:-...`.

## Зачем
- Чтобы политика trigger/hysteresis была одинаковой при любом запуске backend.
- Без хардкода порогов в Python: тюнинг делается через env.

## Канонические значения Phase 157.1
- `VETKA_CONTEXT_PACKER_ENABLED=true`
- `VETKA_CONTEXT_PACKER_JEPA_ENABLE=true`
- `VETKA_CONTEXT_PACKER_TOKEN_PRESSURE=0.80`
- `VETKA_CONTEXT_PACKER_DOCS_THRESHOLD=18`
- `VETKA_CONTEXT_PACKER_ENTROPY_THRESHOLD=2.50`
- `VETKA_CONTEXT_PACKER_MODALITY_THRESHOLD=2`
- `VETKA_CONTEXT_PACKER_HYSTERESIS_ON=3`
- `VETKA_CONTEXT_PACKER_HYSTERESIS_OFF=2`
- `VETKA_CONTEXT_PACKER_RECENT_MAX=300`

## Сопутствующие изменения
- `.env.example` обновлен тем же набором переменных.
- `run_vetka.sh` при создании `.env` добавляет эти переменные как стартовый профиль.
