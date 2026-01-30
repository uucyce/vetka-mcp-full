# HAIKU_1: Backend Stop/Cancel Mechanism

## Текущее состояние - 70% готово!

VETKA уже имеет частичную реализацию механизма остановки (Phase 83):
- Встроенный флаг остановки в `QdrantIncrementalUpdater`
- API endpoint `POST /api/scanner/stop` в semantic_routes.py
- Graceful checkpoints между файлами

## Найденные механизмы (с номерами строк)

### qdrant_updater.py
| Маркер | Строка | Код |
|--------|--------|-----|
| STOP_MARKER_1 | 69 | `self._stop_requested: bool = False` - флаг |
| STOP_MARKER_2 | 72 | `def request_stop()` - запрос остановки |
| STOP_MARKER_3 | 82 | `def reset_stop()` - сброс флага |
| STOP_MARKER_4 | 578 | Проверка в `scan_directory()` цикле |
| STOP_MARKER_5 | 314 | Checkpoint в `batch_update()` (фильтр) |
| STOP_MARKER_6 | 344 | Checkpoint в `batch_update()` (embedding) |

### watcher_routes.py
| Маркер | Строка | Код |
|--------|--------|-----|
| STOP_MARKER_7 | 162 | `updater.reset_stop()` перед сканом |
| STOP_MARKER_11 | NEW | Нужен endpoint `/watcher/stop-scan` |

### semantic_routes.py
| Маркер | Строка | Код |
|--------|--------|-----|
| STOP_MARKER_8 | 795 | `updater.request_stop()` в API |
| STOP_MARKER_9 | 799 | Socket emit `scan_stop_requested` |
| STOP_MARKER_10 | 688 | Проверка флага в `rescan()` |

## Рекомендации

### Сильные стороны:
- Безопасное завершение МЕЖДУ файлами (не в середине)
- Graceful shutdown с сохранением статистики
- Socket.IO интеграция готова

### Недостатки:
- Нет endpoint в `/api/watcher/` для остановки
- Нужен timeout для больших деревьев

### Нужно добавить:

```python
# STOP_MARKER_11: watcher_routes.py - новый endpoint
@router.post("/stop-scan")
async def stop_current_scan():
    updater = get_qdrant_updater()
    updater.request_stop()
    await socketio.emit('scan_stop_requested', {'status': 'stopping'})
    return {'success': True}
```
