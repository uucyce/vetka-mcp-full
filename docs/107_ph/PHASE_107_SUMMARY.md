# Phase 107: Chat System Audit Summary

**Date:** 2026-02-02
**Agents:** Haiku (markers) + 2x Sonnet (verification + fix)

---

## Executive Summary

| Issue | Status | Priority | Action |
|-------|--------|----------|--------|
| Rename Button | ✅ Working | - | None |
| New Chat Button | ❌ Missing | HIGH | Add button |
| Scroll-to-Bottom | ❌ Missing | HIGH | Add button |
| CHAT_NAMING | ⚠️ Partial | MEDIUM | Fix 6 locations |
| CHAT_PAGINATION | ❌ No limit/offset | MEDIUM | Implement |
| CHAT_RETENTION | 🔴 CRITICAL | **URGENT** | 4MB file, no limits |
| Tauri Migration | ⚠️ 40% done | LOW | Dual stack OK |

---

## Agent Reports

### 1. Haiku - UI Markers

| Feature | Status | Location |
|---------|--------|----------|
| Rename (sidebar) | ✅ | ChatSidebar.tsx:257 |
| Rename (header) | ✅ | ChatPanel.tsx:1913 |
| New Chat | ❌ Missing | Need to add |
| Scroll-to-bottom | ❌ Missing | Need to add |

**Markers to add:**
- `MARKER_CHAT_NEW_BUTTON`
- `MARKER_CHAT_SCROLL_BUTTON`

### 2. Sonnet - Verification

| Marker | Verified | Notes |
|--------|----------|-------|
| CHAT_PAGINATION | ✅ Valid | No limit/offset in get_all_chats() |
| CHAT_RETENTION | ✅ **CRITICAL** | 4MB file, 122 chats, no cleanup |
| CHAT_NAMING | ⚠️ Partial | Fixed in 1 place, broken in 6 |
| Tauri | ⚠️ 40% | Dual stack intentional |

### 3. Sonnet - NAMING Fix Analysis

**Found 6 locations using node_path instead of semantic key:**
- Line 485: provider_registry
- Line 660: after workflow
- Line 737: @mention direct
- Line 997: another location
- Line 1050: user input event
- Line 1832: agent chain

**Solution:** Add `extract_semantic_key()` function, replace all 6 instances.

---

## Priority Actions

### 🔴 P0 - URGENT
1. **RETENTION Policy** - 4MB file growing unbounded
   - Add max_chats limit (1000)
   - Add max_age (90 days)
   - Add size check (10MB)

### 🟡 P1 - HIGH
2. **New Chat Button** - Users can't start new conversations
3. **Scroll-to-Bottom** - Users can't return to latest messages
4. **PAGINATION** - load end of chat by default

### 🟢 P2 - MEDIUM
5. **CHAT_NAMING** - Fix 6 locations to use semantic keys
6. **Schema Migration** - Backfill context_type for old chats

---

## Files Modified

| File | Changes |
|------|---------|
| `docs/107_ph/haiku_markers_report.md` | Created |
| `docs/107_ph/sonnet_verification_report.md` | Created |
| `docs/107_ph/sonnet_fix_naming_report.md` | Created |

---

## Next Steps

1. [ ] Implement RETENTION policy (P0)
2. [ ] Add New Chat button (P1)
3. [ ] Add Scroll-to-bottom button (P1)
4. [ ] Add PAGINATION with limit/offset (P1)
5. [ ] Fix CHAT_NAMING in 6 locations (P2)
6. [ ] Continue Tauri migration (Phase 100.4+)

---

## Contradiction Resolved

**Sonnet Verifier** said: "CHAT_NAMING already fixed"
**Sonnet Fixer** found: "6 locations still use node_path"

**Resolution:** One location (Ollama handler) was fixed, 6 others were not. The marker is PARTIALLY fixed.
