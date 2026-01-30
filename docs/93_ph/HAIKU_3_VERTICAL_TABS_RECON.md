# Phase 93: Vertical Tabs Reconnaissance

**Agent:** Haiku
**Date:** 2026-01-25
**Status:** COMPLETE

---

## 1. COMPONENT

**Path:** `client/src/components/ModelDirectory.tsx`
**Section:** CATEGORY_GROUPS constant + sidebar render

---

## 2. CURRENT TABS

### Category Groups:

| Group | Label | Icon | Filters | Default |
|-------|-------|------|---------|---------|
| models | Models | Bot | all, local, free | Expanded |
| pricing | By Price | DollarSign | cheap, premium | Collapsed |
| special | Special | Layers | voice, mcp | Collapsed |

### Filter Types:
```typescript
type FilterType = 'all' | 'local' | 'free' | 'cheap' | 'premium' | 'voice' | 'mcp';
```

---

## 3. STYLING

### Sidebar Dimensions:
| Property | Value |
|----------|-------|
| Width | 54px |
| Panel total | 380px |
| Item padding | 12px vertical |
| Icon size | 16px |

### Colors (Grayscale):
| State | Background | Border |
|-------|------------|--------|
| Normal | transparent | none |
| Hover | #1a1a1a | none |
| Active | #222 | left #555 |
| Expanded | #1a1a1a | left #444 |

---

## 4. MARKERS FOUND

| Phase | Description |
|-------|-------------|
| 80.3 | ModelDirectory redesign with sidebar |
| 80.19 | Direct model addition to groups |
| 57, 57.1, 57.9 | API key detection |
| 56.6 | Group creation mode |
| 60.5 | Voice models support |

**No MARKER_* prefixes found in this component.**

---

## 5. ICONS (lucide-react)

| Filter | Icon |
|--------|------|
| Models | Bot |
| By Price | DollarSign |
| Special | Layers |
| Local | Home |
| Free | Zap |
| Premium | Crown |
| Voice | Mic |
| MCP | Terminal |
| API Keys | Key |

---

## 6. HOW TO ADD "OPENROUTER" TAB

### Step 1: Add to CATEGORY_GROUPS
```typescript
{
  id: 'providers',
  label: 'By Provider',
  icon: Cloud,  // or Server, Globe
  filters: ['openrouter', 'direct'],
  expanded: false
}
```

### Step 2: Extend FilterType
```typescript
type FilterType = '...' | 'openrouter' | 'direct';
```

### Step 3: Add filter logic in useMemo
```typescript
case 'openrouter':
  return models.filter(m =>
    m.provider === 'openrouter' ||
    m.id.includes('/')
  );
case 'direct':
  return models.filter(m =>
    ['openai', 'anthropic', 'xai', 'google'].includes(m.provider)
  );
```

### Step 4: Add icon
```typescript
import { Cloud } from 'lucide-react';
```

---

## 7. RECOMMENDED STRUCTURE

```
SIDEBAR (54px)
├─ Models (Bot)
│  ├─ All
│  ├─ Local
│  └─ Free
├─ By Price (DollarSign)
│  ├─ Cheap
│  └─ Premium
├─ By Provider (Cloud) ← NEW
│  ├─ OpenRouter
│  └─ Direct API
├─ Special (Layers)
│  ├─ Voice
│  └─ MCP
└─ API Keys (Key)
```

---

## NOTES

- All styling is inline (no CSS classes)
- Expand/collapse state managed per group
- Active filter highlighted with left border
- Icons are 16px lucide-react SVGs
