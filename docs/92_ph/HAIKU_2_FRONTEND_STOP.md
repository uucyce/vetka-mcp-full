# HAIKU_2: Frontend Stop Button UI

## Текущий UI сканирования

**Progress показывается:**
- Progress bar (ScanPanel.tsx lines 602-610): 10px голубой градиент
- File counter (lines 578-587): `45/156` во время скана, `27 files` после

**Текущие состояния:**
- `isScanning` (line 230): Boolean
- `progress` (line 231): 0-100%
- `currentFiles/totalFiles` (lines 232-233)

## Предлагаемое размещение кнопки Stop

**ЛУЧШИЙ ВАРИАНТ: Рядом с progress bar (inline)**

Почему:
- Header уже переполнен (carousel, stats, clear button)
- Progress bar - место где глаза пользователя во время скана
- Кнопка появляется ТОЛЬКО когда `isScanning === true`

**Визуал:**
- 24×24px кнопка (меньше чем clear-btn)
- Серая → красная при hover
- Иконка `×` или `Stop`

## Необходимые состояния и props

### ScanPanel.tsx маркеры:

```typescript
// STOP_UI_MARKER_1: Line ~240 (после isClearing)
const [isStopping, setIsStopping] = useState(false);

// STOP_UI_MARKER_2: Line ~420 (после handlePathKeyDown)
const handleStopScan = useCallback(async () => {
  setIsStopping(true);
  try {
    await fetch(`${API_BASE}/watcher/stop-scan`, { method: 'POST' });
    // Socket event обновит состояние
  } catch (err) {
    console.error('[ScanPanel] Stop error:', err);
  } finally {
    setIsStopping(false);
  }
}, []);

// STOP_UI_MARKER_3: Line ~602 (progress bar container)
{(isScanning || progress > 0) && (
  <div className="scan-progress-container">
    <div className="scan-progress-bar">...</div>
    {isScanning && (
      <button className="stop-scan-btn" onClick={handleStopScan}>
        {isStopping ? '...' : '×'}
      </button>
    )}
  </div>
)}
```

### ScanPanel.css маркеры:

```css
/* STOP_UI_MARKER_4: После .scan-progress-bar */
.scan-progress-container {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 12px 8px 12px;
}

/* STOP_UI_MARKER_5: Новый стиль */
.stop-scan-btn {
  width: 24px;
  height: 24px;
  background: transparent;
  border: 1px solid #333;
  border-radius: 4px;
  color: #888;
  cursor: pointer;
  font-size: 14px;
  font-weight: bold;
}

.stop-scan-btn:hover {
  background: #8b3a3a;
  border-color: #d45a5a;
  color: #f87171;
}
```

## Маркеры для изменений

| Маркер | Файл | Описание |
|--------|------|----------|
| STOP_UI_MARKER_1 | ScanPanel.tsx | Добавить `isStopping` state |
| STOP_UI_MARKER_2 | ScanPanel.tsx | Добавить `handleStopScan` handler |
| STOP_UI_MARKER_3 | ScanPanel.tsx | Обернуть progress bar + stop button |
| STOP_UI_MARKER_4 | ScanPanel.css | Контейнер для progress + button |
| STOP_UI_MARKER_5 | ScanPanel.css | Стили stop button |
