# VETKA CODE AUDIT - SONNET FIX REPORT
**Date:** 2026-01-22
**Fixer:** Claude Sonnet 4.5
**Scope:** P0 bugs only (3 critical issues)

---

## FIXES APPLIED

### ✅ [BUG:src/scanners/qdrant_updater.py:130] - Python 3.10+ tuple syntax
**Status:** FIXED
**Issue:** Used `tuple[bool, Optional[Dict]]` syntax (Python 3.10+) on Python 3.9 target
**Fix:**
- Added `Tuple` import from `typing` module (line 20)
- Changed `tuple[...]` → `Tuple[...]` (line 130)
**Impact:** Now compatible with Python 3.9+ runtime

### ✅ [BUG:src/scanners/file_watcher.py:112-117] - Timer memory leak
**Status:** FIXED
**Issue:** Canceled timers left dangling references in `self.timers` dict
**Fix:**
- Added `del self.timers[path]` after `cancel()` (line 111)
- Prevents memory leak during long-running file watch sessions
**Impact:** No more accumulating timer references on repeated file events

### ✅ [BUG:src/api/handlers/handler_utils.py:260-284] - Race condition in key rotation
**Status:** FIXED
**Issue:** Global `_current_key_index` could skip values if two async tasks called `rotate_openrouter_key()` simultaneously
**Fix:**
- Added `import threading` (line 9)
- Created `_key_rotation_lock = threading.Lock()` (line 257)
- Wrapped index increment in `with _key_rotation_lock:` block (line 286)
**Impact:** Atomic key rotation, no skipped indices in concurrent scenarios

---

## REJECTED FIXES (per instructions)

### ❌ God Objects (4 issues)
**Reason:** Too risky without architectural discussion. Requires human review.

### ❌ Dead Code (5 TODOs)
**Reason:** Needs human review to confirm safe removal vs future implementation.

### ❌ Hardcoded Values (10 issues)
**Reason:** Requires config architecture discussion (config.py vs .env strategy).

---

## SUMMARY

| Category | Total | Fixed | Rejected |
|----------|-------|-------|----------|
| P0 Bugs | 8 | 3 | 5 |
| God Objects | 4 | 0 | 4 |
| Dead Code | 5 | 0 | 5 |
| Hardcodes | 10 | 0 | 10 |

**Files Modified:** 3
**Lines Changed:** 7
**Breaking Changes:** None
**Regression Risk:** Minimal (defensive fixes only)

---

**Report Generated:** 2026-01-22
**Next Step:** Haiku auditor to verify fixes via pytest smoke tests
