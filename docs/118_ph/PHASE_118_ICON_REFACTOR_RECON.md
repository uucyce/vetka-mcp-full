# Phase 118: Icon Refactor — Recon Report

**Date:** 2026-02-07
**Status:** RECON COMPLETE
**Task:** Перенос иконок чата/артефакта к поисковой панели

---

## Problem Statement

При открытии чата иконки (Chat + Artifact) переезжают вниз экрана и мешают работе.
Нужно:
1. Убрать иконку чата когда чат открыт (она не нужна)
2. Привязать иконку артефакта к search bar (рядом со Scanner icon)
3. Учесть dual-position чата (left/right)

---

## Current Architecture

### Files Involved

| File | Purpose | Key Lines |
|------|---------|-----------|
| `client/src/App.tsx` | Главный layout, иконки когда чат закрыт | 240-249, 410-428, 541-713 |
| `client/src/components/chat/ChatPanel.tsx` | Chat panel + header + search | 1584-1588, 1940-1968, 2169-2191 |
| `client/src/components/search/UnifiedSearchBar.tsx` | Search bar component | 33-144 |

---

## Markers Added (MARKER_118.x)

### App.tsx

| Marker | Line | Description |
|--------|------|-------------|
| `MARKER_118.1A` | ~241 | `getIconsLeft()` — динамическое позиционирование (ПРОБЛЕМА) |
| `MARKER_118.1B` | ~411 | `ChestIcon` — компонент иконки артефакта |
| `MARKER_118.2A` | ~542 | Контейнер когда чат ЗАКРЫТ — SearchBar + иконки справа |
| `MARKER_118.2B` | ~656 | Контейнер когда чат ОТКРЫТ — иконки внизу (ПРОБЛЕМА!) |

### ChatPanel.tsx

| Marker | Line | Description |
|--------|------|-------------|
| `MARKER_118.3A` | ~1584 | `ScannerIcon` — ЦЕЛЕВОЕ МЕСТО для иконки артефакта |
| `MARKER_118.3B` | ~1940 | Кнопка Scanner — сюда добавить ChestIcon |
| `MARKER_118.3C` | ~2170 | UnifiedSearchBar в ChatPanel — альтернативное место |

---

## Current Flow (Visual)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CHAT CLOSED                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────┐  ┌──┐                                     │
│  │  🔍 Search...        │  │💬│  ← Chat icon (36x36)                │
│  └──────────────────────┘  │📦│  ← Artifact icon (36x36)            │
│         (360px)            └──┘                                      │
│                                                                      │
│  Position: fixed, top: 16px, left: 16px                             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        CHAT OPEN                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────┐                                      │
│  │     Chat Panel (360px)     │                                      │
│  │  ┌──────────────────────┐  │                                      │
│  │  │ 🔍 Search code/docs  │  │  ← Search inside chat               │
│  │  └──────────────────────┘  │                                      │
│  │                            │                                      │
│  │     [messages...]          │                                      │
│  │                            │                                      │
│  └────────────────────────────┘                                      │
│                                                                      │
│  ┌──┐ ┌──┐                                                          │
│  │💬│ │📦│  ← Icons floating at BOTTOM (48x48) — PROBLEM!           │
│  └──┘ └──┘                                                          │
│                                                                      │
│  Position: fixed, bottom: 20px, left: getIconsLeft()                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CHAT OPEN (TARGET)                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────┐                      │
│  │  ChatPanel Header:                         │                      │
│  │  [Chat] [Group] [Call]  ──── [📦][📁][↔][✕]│                      │
│  │                              ↑   ↑         │                      │
│  │                         Artifact Scanner   │                      │
│  ├────────────────────────────────────────────┤                      │
│  │  🔍 Search code/docs...                    │                      │
│  ├────────────────────────────────────────────┤                      │
│  │     [messages...]                          │                      │
│  │                                            │                      │
│  └────────────────────────────────────────────┘                      │
│                                                                      │
│  NO floating icons at bottom!                                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Step 1: Remove floating icons when chat open (App.tsx)
- DELETE block `MARKER_118.2B` (lines 656-713)
- This removes the problematic bottom-floating icons

### Step 2: Add ChestIcon to ChatPanel header (ChatPanel.tsx)
- Import or copy `ChestIcon` component
- Add artifact button next to Scanner button (MARKER_118.3B, ~line 1940)
- Wire up: `onClick={() => setIsArtifactOpen(!isArtifactOpen)}`
- Need to pass `isArtifactOpen`, `setIsArtifactOpen`, `selectedNode` as props

### Step 3: Handle dual-position (left/right)
- ChatPanel has `chatPosition` state ('left' | 'right')
- Icons should work regardless of position
- No additional changes needed if icons are in header

### Step 4: Props threading
- App.tsx needs to pass to ChatPanel:
  - `isArtifactOpen: boolean`
  - `setIsArtifactOpen: (open: boolean) => void`
  - `selectedNode: string | null`

---

## Complexity Assessment

| Aspect | Level | Notes |
|--------|-------|-------|
| Code changes | MEDIUM | 2 files, ~50 lines |
| Risk | LOW | UI-only, no backend |
| Testing | Manual | Check both chat positions |
| Dependencies | None | No new packages |

---

## Files to Modify

1. **App.tsx**
   - Remove `MARKER_118.2B` block (floating icons when chat open)
   - Add props to ChatPanel: `isArtifactOpen`, `setIsArtifactOpen`, `selectedNode`

2. **ChatPanel.tsx**
   - Add `ChestIcon` component (copy from App.tsx)
   - Add artifact button in header next to ScannerIcon
   - Accept new props

---

## Search Commands for Verification

```bash
# Find all markers
grep -n "MARKER_118" client/src/App.tsx client/src/components/chat/ChatPanel.tsx

# Find ChestIcon usages
grep -n "ChestIcon" client/src/App.tsx

# Find getIconsLeft
grep -n "getIconsLeft" client/src/App.tsx
```

---

## Next Steps

1. User approval of plan
2. Execute implementation (Dragon Silver or manual)
3. Test with chat in both positions (left/right)
4. Remove markers after completion

---

---

## Implementation Status: DONE

### Changes Made:

**App.tsx:**
- REMOVED: `getIconsLeft()` function (no longer needed)
- REMOVED: MARKER_118.2B block (floating icons when chat open)
- KEPT: Icons when chat closed (top-left, next to search bar)

**ChatPanel.tsx:**
- ADDED: `ChestIcon` component (lines 1591-1609)
- ADDED: Artifact button in header (lines 1961-2003)
- Button placement: `[Spacer] [Artifact] [Scanner] [Position] [Close]`

### Build Status:
- My changes: CLEAN
- Pre-existing TS errors: 40+ (unrelated to Phase 118)

---

**Report generated by:** Opus 4.5 (Recon Phase)
**Haiku scouts:** 3 parallel agents
**Duration:** ~2 minutes

**Implementation by:** Opus 4.5
**Duration:** ~5 minutes
