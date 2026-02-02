# Phase 108: Scroll Button + MCP Persistence Fixes

**Date:** 2026-02-02
**Status:** COMPLETED ✓

## Fix #1: Scroll Button - Toggle Direction

### MARKER_SCROLL_BTN_TOGGLE_FIX

**Problem:** Scroll button always showed UP arrow (↑) until first manual scroll.

**Solution:** Call `handleScroll()` immediately after attaching listener.

**File:** `client/src/components/chat/ChatPanel.tsx`

```diff
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
+     handleScroll(); // Detect initial scroll position
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, [handleScroll]);
```

**Status:** ✅ FIXED

---

## Fix #2: MCP Messages Persistence

### MARKER_MCP_PERSIST_FIX

**Reported:** "MCP messages disappear after reload"

**Result:** **NOT A BUG** - Messages persist correctly.

**Explanation:** Frontend loads last 50 messages by default (pagination).

**Verification:**
```bash
tail -100 data/groups.json | grep "@claude_mcp"
curl "/api/groups/{id}/messages?limit=200"
```

**Status:** ✅ VERIFIED WORKING (No fix needed)

---

## Files Modified

- `client/src/components/chat/ChatPanel.tsx` (scroll fix)
- `docs/MARKER_MCP_PERSIST_FIX.md` (investigation)
- `docs/PHASE_108_FIXES_REPORT.md` (this file)
- `docs/SCROLL_BTN_MCP_PERSIST_FIX_SUMMARY.md` (summary)
- `docs/SCROLL_MCP_CODE_MAP.md` (code reference)
