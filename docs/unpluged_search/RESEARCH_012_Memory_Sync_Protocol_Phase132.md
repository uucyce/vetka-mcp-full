# Memory Sync Protocol (Snapshot + Diff)
**Рекомендуемая фаза:** 132
**Статус:** Не имплементировано
**Приоритет:** СРЕДНИЙ
**Источник:** Беседы агентов, Phase 77-78 proposal

## Описание
Snapshot-based diff algorithm для памяти с user curation через Hostess agent. Включает trash memory с recovery.

## Текущее состояние
- Память сохраняется без sync protocol
- Нет diff-based updates
- Нет trash/recovery layer
- Нет user curation

## Технические детали
- MemorySnapshot dataclass
- DiffResult: added/modified/deleted tracking
- Soft-delete trash layer (TTL 90 days)
- Hostess Memory Curator Dialog
- Auto-compress: node_modules → full, docs → summary
- Age-based embedding compression (768D→384D→256D→64D via PCA)

## Шаги имплементации
1. Создать MemorySnapshot + DiffResult classes
2. Реализовать snapshot diff algorithm
3. Добавить Qdrant "vetka_trash" collection
4. Создать restore_from_trash() + cleanup_expired_trash()
5. Hostess curation UI (interactive prompts)

## Ожидаемый результат
Контролируемое управление памятью с возможностью восстановления

---
