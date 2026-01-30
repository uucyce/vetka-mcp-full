# Phase 90.3: Testing Guide

## Quick Test Scenarios

### Scenario 1: Normal Operation (Qdrant Ready)

**Setup:**
- Start VETKA with Qdrant running
- Ensure docs/90_ph is being watched

**Test:**
```bash
# Create test file
echo "# Test File" > docs/90_ph/test_90.3_normal.md

# Check terminal output for:
# [Watcher] ✅ Indexed to Qdrant: /path/to/test_90.3_normal.md
```

**Expected:** Immediate indexing with ✅ emoji

---

### Scenario 2: Delayed Qdrant (Retry Success)

**Setup:**
- Start VETKA with Qdrant disabled
- Wait for watcher to start
- Enable Qdrant
- Create file within 2 seconds of enabling

**Test:**
```bash
# While Qdrant is starting up...
echo "# Test Retry" > docs/90_ph/test_90.3_retry.md

# Check terminal output for:
# [Watcher] ✅ Indexed to Qdrant: /path/to/test_90.3_retry.md
# (may appear after ~2 second delay)
```

**Expected:** File indexed after 2-second retry delay

---

### Scenario 3: Qdrant Unavailable (Skip with Warning)

**Setup:**
- Start VETKA with Qdrant permanently disabled
- OR stop Qdrant after VETKA starts

**Test:**
```bash
# With Qdrant disabled
echo "# Test Skip" > docs/90_ph/test_90.3_skip.md

# Check terminal output for:
# [Watcher] ⚠️ SKIPPED (Qdrant unavailable after retry): /path/to/test_90.3_skip.md
```

**Expected:** Clear SKIPPED warning with ⚠️ emoji after 2-second retry attempt

---

### Scenario 4: Qdrant Error (Error Handling)

**Setup:**
- Start VETKA with Qdrant running
- Corrupt Qdrant collection or trigger error

**Test:**
```bash
echo "# Test Error" > docs/90_ph/test_90.3_error.md

# Check terminal output for:
# [Watcher] ❌ Error updating Qdrant: [error message]
```

**Expected:** Error logged with ❌ emoji

---

## Visual Verification

### Old Behavior (Before Phase 90.3)
```
[Watcher] modified: /path/to/file.md
[Watcher] WARNING: qdrant_client not available (lazy fetch failed), skipping Qdrant index for: /path/to/file.md
```
- Generic WARNING (easy to miss)
- No retry attempt
- No user-friendly status

### New Behavior (After Phase 90.3)
```
[Watcher] modified: /path/to/file.md
[Watcher] ⚠️ SKIPPED (Qdrant unavailable after retry): /path/to/file.md
```
- Clear SKIPPED status with emoji
- Retry attempted (2s delay)
- User-friendly message

---

## Automated Testing

### Check Markers
```bash
# Verify markers are present
grep -n "MARKER_90.3" src/scanners/file_watcher.py

# Should show:
# 384:        # MARKER_90.3_START: Fix qdrant client retry
# 404:        # MARKER_90.3_END
```

### Check Import
```bash
# Verify retry_time import doesn't conflict
grep "import time as retry_time" src/scanners/file_watcher.py

# Should show:
# 390:            import time as retry_time
```

### Check Emoji Output
```bash
# Start VETKA and watch logs for emoji indicators
tail -f logs/vetka.log | grep -E "✅|❌|⚠️"
```

---

## Performance Testing

### Measure Delay Impact

**Before:**
- No retry → 0ms overhead on failure
- But silent data loss

**After:**
- 2-second retry → 2000ms overhead on failure
- But only on first fetch failure
- Prevents data loss

**Test:**
```bash
# Time the operation
time echo "# Test" > docs/90_ph/test_timing.md

# With Qdrant ready: ~0ms (no delay)
# With Qdrant delayed: ~2000ms (retry delay)
# With Qdrant unavailable: ~2000ms (retry + skip)
```

---

## Regression Testing

### Ensure Existing Features Work

1. **Debounce:** Rapid edits still coalesced
2. **Socket Emit:** Frontend still receives events
3. **Adaptive Scanner:** Heat scores still tracked
4. **State Persistence:** Watched dirs still saved
5. **Bulk Operations:** git checkout still detected

**Test All:**
```bash
# Run existing watchdog tests
python -m pytest tests/test_file_watcher.py -v

# OR manual smoke test
python src/scanners/file_watcher.py docs/90_ph
# Create/modify/delete files
# Verify all events logged correctly
```

---

## Known Limitations

### 2-Second Blocking

- Blocks watchdog thread during retry
- Only affects files processed during Qdrant startup
- Future Phase 90.4 will use non-blocking queue

### Single Retry

- Only retries once (not loop)
- After 2nd failure, file skipped
- Future Phase 90.4 will queue for later

### No Persistent Queue

- Skipped files not saved for later
- Requires manual re-scan or file re-save
- Future Phase 90.4 will add persistent queue

---

## Troubleshooting

### "SKIPPED" appearing too often?

**Check:**
1. Is Qdrant running? `curl http://localhost:6333/collections`
2. Is Qdrant manager initialized? Check logs for "Qdrant manager initialized"
3. Is lazy fetch working? Check logs for "Phase 80.17: Lazy fetched qdrant_client"

**Fix:**
- Ensure Qdrant starts before watcher
- Or accept 2s delay for files during startup

### No retry happening?

**Check:**
1. First fetch returns None? Add debug log in `_get_qdrant_client()`
2. Import working? Verify `import time as retry_time` line 390

**Debug:**
```python
# Add temporary logging
print(f"[DEBUG] First fetch: {qdrant_client}")
import time as retry_time
retry_time.sleep(2)
qdrant_client = self._get_qdrant_client()
print(f"[DEBUG] Second fetch: {qdrant_client}")
```

---

## Success Criteria

- ✅ Files indexed when Qdrant ready
- ✅ Files indexed when Qdrant delayed (within 2s)
- ✅ Clear SKIPPED warning when Qdrant unavailable
- ✅ No silent failures
- ✅ Backward compatible (no breaking changes)
- ✅ All markers present and searchable

---

## Next Steps After Testing

1. Verify all scenarios pass
2. Check logs for any unexpected behavior
3. Measure performance impact
4. Plan Phase 90.4 queue implementation
5. Document any edge cases discovered
