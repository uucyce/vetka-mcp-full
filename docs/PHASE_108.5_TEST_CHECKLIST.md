# Phase 108.5: Group Rename - Test Checklist

**Status:** Ready for Testing
**Date:** 2026-02-02
**Tester:** _____________

---

## Pre-Test Setup

- [ ] Server running: `python src/main.py`
- [ ] Client running: `cd client && npm run dev`
- [ ] Browser open: `http://localhost:3000`
- [ ] Console open (F12) for debug logs

---

## Test 1: Create Group and Rename

### Steps
1. [ ] Open Group Creator panel (left sidebar)
2. [ ] Add 2+ agents (e.g., PM, Dev)
3. [ ] Enter group name: "Test Group Original"
4. [ ] Click "Create Group"
5. [ ] Verify group appears in chat with name "Test Group Original"
6. [ ] Click on group name in header
7. [ ] Enter new name: "Test Group Renamed"
8. [ ] Click OK

### Expected Results
- [ ] Header updates to "Test Group Renamed" immediately
- [ ] Console shows: `[ChatPanel] Phase 108.5: Renamed group to "Test Group Renamed"`
- [ ] No errors in console

### API Verification
```bash
# Check groups.json for updated name
cat data/groups.json | jq '.groups | to_entries[] | select(.value.name == "Test Group Renamed")'
```

---

## Test 2: Reload and Verify Persistence

### Steps
1. [ ] With renamed group still active
2. [ ] Press F5 to reload page
3. [ ] Wait for page to load
4. [ ] Open chat history (left sidebar)
5. [ ] Click on "Test Group Renamed" in history

### Expected Results
- [ ] Group loads with name "Test Group Renamed"
- [ ] Console shows: `[ChatPanel] Phase 108.5: Loaded group name: "Test Group Renamed"`
- [ ] Header displays correct name
- [ ] Chat history shows updated name

---

## Test 3: Empty Name Validation

### Steps
1. [ ] Click on group name in header
2. [ ] Clear the text field (delete all text)
3. [ ] Click OK or press Enter

### Expected Results
- [ ] Rename is cancelled (no API call)
- [ ] Name remains unchanged
- [ ] No console errors

---

## Test 4: Same Name (No-Op)

### Steps
1. [ ] Click on group name in header
2. [ ] Leave name unchanged
3. [ ] Click OK

### Expected Results
- [ ] Rename is cancelled (no API call)
- [ ] Name remains the same
- [ ] No console errors

---

## Test 5: Multiple Renames

### Steps
1. [ ] Rename group to "Name A"
2. [ ] Verify update
3. [ ] Rename group to "Name B"
4. [ ] Verify update
5. [ ] Rename group to "Name C"
6. [ ] Verify update

### Expected Results
- [ ] Each rename succeeds
- [ ] Header updates each time
- [ ] Final name is "Name C"
- [ ] groups.json shows "Name C"

---

## Test 6: Regular Chat Rename (Regression)

### Steps
1. [ ] Create or open regular chat (not group)
2. [ ] Click on chat name in header
3. [ ] Enter new name: "Regular Chat Test"
4. [ ] Click OK

### Expected Results
- [ ] Chat renames successfully
- [ ] Uses PATCH /api/chats/{id} endpoint
- [ ] No interference with group rename logic
- [ ] Console shows chat rename log (not group)

---

## Test 7: API Direct Test

### Using curl
```bash
# Get first group ID
GROUP_ID=$(cat data/groups.json | jq -r '.groups | keys[0]')
echo "Testing with group: $GROUP_ID"

# Rename via API
curl -X PATCH "http://localhost:8000/api/groups/$GROUP_ID" \
  -H "Content-Type: application/json" \
  -d '{"name": "API Test Name"}' \
  | jq '.'
```

### Expected Response
```json
{
  "success": true,
  "group_id": "<group-id>",
  "name": "API Test Name"
}
```

### Verification
```bash
# Check groups.json
cat data/groups.json | jq ".groups[\"$GROUP_ID\"].name"
# Should output: "API Test Name"
```

---

## Test 8: Error Handling - Non-Existent Group

### Using curl
```bash
curl -X PATCH "http://localhost:8000/api/groups/fake-id-12345" \
  -H "Content-Type: application/json" \
  -d '{"name": "Should Fail"}' \
  -w "\nHTTP Status: %{http_code}\n"
```

### Expected Results
- [ ] HTTP Status: 404
- [ ] Response: `{"detail": "Group fake-id-12345 not found"}`

---

## Test 9: Edge Case - Special Characters

### Steps
1. [ ] Click on group name
2. [ ] Enter name with special chars: "Test 🚀 Group (Beta)"
3. [ ] Click OK

### Expected Results
- [ ] Rename succeeds
- [ ] Special characters preserved
- [ ] groups.json contains correct UTF-8
- [ ] Header displays correctly

---

## Test 10: Concurrent Rename (Advanced)

### Steps
1. [ ] Open same group in 2 browser tabs
2. [ ] Tab 1: Click rename, type "Name From Tab 1"
3. [ ] Tab 2: Click rename, type "Name From Tab 2"
4. [ ] Tab 1: Submit first
5. [ ] Tab 2: Submit second
6. [ ] Reload both tabs

### Expected Results
- [ ] Last rename wins (Tab 2's name)
- [ ] No data corruption in groups.json
- [ ] No race condition errors in server logs

---

## Test 11: Load Multiple Groups

### Steps
1. [ ] Create Group A, rename to "Alpha"
2. [ ] Create Group B, rename to "Beta"
3. [ ] Create Group C, rename to "Gamma"
4. [ ] Open chat history
5. [ ] Click on each group

### Expected Results
- [ ] Each group loads with correct name
- [ ] No name conflicts
- [ ] Switching between groups updates header correctly

---

## Test 12: Whitespace Handling

### Steps
1. [ ] Click on group name
2. [ ] Enter: "   Spaced Name   "
3. [ ] Click OK

### Expected Results
- [ ] Whitespace is trimmed
- [ ] Stored as: "Spaced Name"
- [ ] Header shows: "Spaced Name"

---

## Performance Checks

### Metrics to Monitor
- [ ] Rename latency: < 100ms
- [ ] Console logs clear and informative
- [ ] No memory leaks after 10+ renames
- [ ] groups.json file size reasonable

### Server Logs to Check
```bash
# Check server logs for rename operations
tail -f server.log | grep "Renamed group"
```

Expected output:
```
[GroupChat] Renamed group abc-123: 'Old Name' -> 'New Name'
```

---

## Regression Checks

- [ ] Chat creation still works
- [ ] Group creation still works
- [ ] Message sending still works
- [ ] Group chat history loads correctly
- [ ] No TypeScript errors in browser console
- [ ] No Python errors in server console

---

## Documentation Verification

- [ ] README updated (if applicable)
- [ ] API docs show PATCH /api/groups/{id}
- [ ] Markers present in code (MARKER_GROUP_RENAME_*)
- [ ] Phase 108.5 docs complete

---

## Sign-Off

### Test Results
- Total Tests: 12
- Passed: _____ / 12
- Failed: _____ / 12
- Blocked: _____ / 12

### Issues Found
1. _____________________________
2. _____________________________
3. _____________________________

### Tester Notes
```
_____________________________________________________
_____________________________________________________
_____________________________________________________
```

### Final Status
- [ ] ✅ APPROVED - Ready for production
- [ ] ⚠️  APPROVED WITH NOTES - Minor issues
- [ ] ❌ REJECTED - Needs fixes

**Tester Signature:** _____________
**Date:** _____________
**Time:** _____________
