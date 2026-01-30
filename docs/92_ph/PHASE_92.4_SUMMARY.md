# Phase 92.4: Unified Scan Panel

**Date:** 2026-01-25
**Status:** COMPLETED

---

## Summary

Unified `ScannerPanel` and `ScanProgressPanel` into a single `ScanPanel` component with inline path input (no popup dialog).

---

## Changes Made

### 1. New Component: `ScanPanel.tsx`
**Path:** `client/src/components/scanner/ScanPanel.tsx`

Combines features from both panels:
- **From ScannerPanel:** Carousel source selector, Add Folder, watched directories list, Clear All
- **From ScanProgressPanel:** Progress bar, file counter, scanned files list, 300ms hover preview, camera fly-to

### 2. New CSS: `ScanPanel.css`
**Path:** `client/src/components/scanner/ScanPanel.css`

Unified styles with VETKA dark theme.

### 3. Updated `ChatPanel.tsx`
- Replaced imports: `ScannerPanel` + `ScanProgressPanel` → `ScanPanel`
- Single component renders in scanner tab
- Removed separate ScanProgressPanel render

### 4. Updated `scanner/index.ts`
- Added `ScanPanel` export
- Kept legacy `ScannerPanel` export for backwards compatibility

---

## Key Features

### Inline Path Input (No Popup!)
```
┌─────────────────────────────────────────────────┐
│ [/path/to/folder                          ] [+] │
└─────────────────────────────────────────────────┘
```
- Text input with placeholder `/path/to/folder`
- Press Enter or click [+] to add
- No popup dialog needed

### Unified Layout
```
┌─────────────────────────────────────────────────────┐
│ [◀] Local Files [▶]         45/156 files  [🗑] [▲] │
├─────────────────────────────────────────────────────┤
│ ██████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │  ← 10px progress
├─────────────────────────────────────────────────────┤
│ [/path/to/folder                            ] [+] │  ← Inline input
├─────────────────────────────────────────────────────┤
│ ● /Users/dan/Documents/project          150 files │  ← Watched dirs
│ ◐ /Users/dan/Downloads                  scanning  │
├─────────────────────────────────────────────────────┤
│ Recently scanned — Click to fly                    │
│ ✓ src/api/routes.py                       → [🎯]  │  ← Scanned files
│ ✓ src/api/handlers.py                     → [🎯]  │
│ ✓ src/memory/engram.py                    → [🎯]  │
├─────────────────────────────────────────────────────┤
│ ═══════════════════ drag handle ═══════════════════│
└─────────────────────────────────────────────────────┘
```

---

## Feature Checklist

| Feature | Status |
|---------|--------|
| Carousel source selector | ✅ |
| Inline path input (no popup) | ✅ |
| 10px progress bar | ✅ |
| File counter: 45/156 files | ✅ |
| Watched directories list | ✅ |
| Scanned files list (max 20) | ✅ |
| 300ms hover preview | ✅ |
| Click → camera fly-to | ✅ |
| Small trash icon for Clear All | ✅ |
| Resizable via drag (bottom) | ✅ |
| Collapsible/expandable | ✅ |
| Coming soon for other sources | ✅ |

---

## Files Modified

| File | Action | Summary |
|------|--------|---------|
| `ScanPanel.tsx` | NEW | Unified component |
| `ScanPanel.css` | NEW | Unified styles |
| `ChatPanel.tsx` | EDIT | Use ScanPanel instead of two panels |
| `scanner/index.ts` | EDIT | Export ScanPanel |

---

## Future Plans (User Request)

> "В будущем хочу сделать, чтобы окно поиска было единым окном для поиска и сканирования сразу. Чтобы файлы через Ветку можно было искать те что на жестком диске и из результатов отправлять на сканирование. И так же адрес в интернете чтобы вставил и сразу в результатах поиск ответ виде артефакта (который еще и как браузер) и если надо отсканировал страничку."

**Planned:**
1. Unified search + scan bar
2. Disk file search with "send to scan" from results
3. URL input → fetch → artifact preview → optional page scan
4. Browser artifact integration

---

## Testing

1. Start frontend: `npm run dev`
2. Go to Scanner tab
3. Type path in inline input → press Enter or click [+]
4. Watch:
   - Progress bar fills
   - File counter updates
   - Scanned files appear
   - Hover 300ms → preview popup
   - Click file → camera flies to 3D location
5. Carousel through sources (only Local active)
6. Trash icon clears all

---

**Phase 92.4 COMPLETE**
