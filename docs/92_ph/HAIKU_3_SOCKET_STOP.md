# HAIKU_3: Socket.IO Stop Communication

## Текущие socket события

### useSocket.ts (frontend):
- `scan_progress` (line 43): `{progress, status}` - на каждый файл
- `scan_complete` (line 44): `{nodes_count}` - в конце
- CustomEvent dispatch (lines 538-566)

### watcher_routes.py (backend):
- Emit `scan_progress` с `{current, total, file_path, file_size, status}`
- Emit `scan_complete` с `{path, filesCount, nodes_count}`
- **НЕТ** события `scan_stop` / `scan_cancelled`

## Предлагаемый flow для stop

```
[Stop Button] → POST /api/watcher/stop-scan
                    ↓
              Backend: updater.request_stop()
                    ↓
              Socket emit: 'scan_progress' {status: 'stopping'}
                    ↓
              Файл завершается...
                    ↓
              Socket emit: 'scan_stopped' {indexed_count, stopped_at}
                    ↓
              Frontend: показать "Остановлено. 1,234 файла"
```

## Сообщения пользователю

| Фаза | Status | Сообщение |
|------|--------|-----------|
| 1. Click Stop | `stopping` | "Остановка... Завершаю текущий файл..." |
| 2. Last file | `stopping` | "Обработка: last_file.txt" |
| 3. Done | `stopped` | "Остановлено. Индексировано: 1,234 файла" |

**UX важно:** Пользователь должен видеть что система НЕ зависла, а корректно завершает текущий файл.

## Маркеры для изменений

### Backend (watcher_routes.py):

```python
# SOCKET_STOP_MARKER_1: Новый endpoint
@router.post("/stop-scan")
async def stop_scan():
    updater.request_stop()
    await socketio.emit('scan_progress', {
        'status': 'stopping',
        'message': 'Finishing current file...'
    })
    return {'success': True}

# SOCKET_STOP_MARKER_2: В progress_callback добавить проверку
if updater.is_stop_requested():
    await socketio.emit('scan_stopped', {
        'indexed_count': current,
        'stopped_at': file_path
    })
    break
```

### Frontend (useSocket.ts):

```typescript
// SOCKET_STOP_MARKER_3: Обработка 'scan_stopped' события
socket.on('scan_stopped', (data) => {
  window.dispatchEvent(new CustomEvent('scan_stopped', { detail: data }));
});

// SOCKET_STOP_MARKER_4: Нормализация 'stopping' status
if (data.status === 'stopping') {
  // Show "finishing..." UI
}
```

### Frontend (ScanPanel.tsx):

```typescript
// SOCKET_STOP_MARKER_5: Listener для scan_stopped
useEffect(() => {
  const handleScanStopped = (e: CustomEvent) => {
    setIsScanning(false);
    setIsStopping(false);
    // Показать финальную статистику
  };
  window.addEventListener('scan_stopped', handleScanStopped);
  return () => window.removeEventListener('scan_stopped', handleScanStopped);
}, []);
```

## Резюме

| Компонент | Статус | Действие |
|-----------|--------|----------|
| `scan_progress` | ✅ Есть | Добавить status='stopping' |
| `scan_complete` | ✅ Есть | OK |
| `scan_stopped` | ❌ Нет | Добавить новый event |
| HTTP cancel | ❌ Нет | POST /api/watcher/stop-scan |
| Stop flag | ✅ Есть | `updater.request_stop()` готов |
