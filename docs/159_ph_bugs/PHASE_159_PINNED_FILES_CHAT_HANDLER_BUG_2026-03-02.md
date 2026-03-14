# PHASE 159 — Pinned Files + Resize Handle Bug Analysis
**Created:** 2026-03-02
**Updated:** 2026-03-02 (with fix)

---

## 1. UI Terminology

**Resize Handle** (also called: splitter, divider, drag handle) — горизонтальная полоска между секциями, которую пользователь может перетаскивать для изменения размера областей.

В VETKA:
- **Scanner panel**: есть рабочий resize handle
- **Chat panel**: resize handle между pinned files и сообщениями чата

---

## 2. Bug Identified and Fixed

### Problem
Resize handle (горизонтальная полоска) между pinned files и чатом **не работал** из-за неправильной формулы расчёта высоты.

**Old buggy code (ChatPanel.tsx:2084-2091):**
```typescript
// WRONG: использовался неправильный референс для расчёта
const panelTop = messagesContainerRef.current?.getBoundingClientRect().top;
const nextHeight = e.clientY - panelTop - headerHeight;
```

**Fixed code (ChatPanel.tsx:2094-2102):**
```typescript
// CORRECT: используем data-pinned-section элемент
const pinnedSection = document.querySelector('[data-pinned-section]');
if (!pinnedSection) return;
const rect = pinnedSection.getBoundingClientRect();
const currentHeight = e.clientY - rect.top;
const clamped = Math.max(120, Math.min(360, currentHeight));
```

### Markers Added
| Marker | Location | Description |
|--------|----------|--------------|
| `MARKER_159.PIN.RESIZE_FIX` | ChatPanel.tsx:2085-2116 | Исправлена формула resize |
| `MARKER_159.PIN.RESIZE_HOVER` | ChatPanel.tsx:3507-3515 | Добавлен hover эффект |

---

## 3. Changes Made

| File | Line | Change |
|------|------|--------|
| ChatPanel.tsx | 2082-2083 | Добавлены refs для resize |
| ChatPanel.tsx | 2085-2089 | Новый handler `handlePinnedResizeStart` |
| ChatPanel.tsx | 2091-2116 | Исправлен useEffect с правильной формулой |
| ChatPanel.tsx | 3373 | Добавлен `data-pinned-section` атрибут |
| ChatPanel.tsx | 3504-3525 | Добавлен hover эффект + визуальный индикатор при resize |

---

## 4. Visual Improvements

1. **Hover effect**: полоска подсвечивается при наведении
2. **Active resize indicator**: при перетаскивании появляется синяя рамка
3. **Cursor**: `ns-resize` курсор для понятности
