# PHASE 108.3: EXECUTION PLAN - Agent Distribution

**Date:** 2026-02-02
**Status:** IN PROGRESS
**Goal:** Real-time chat visualization + artifacts integration

---

## AGENT DISTRIBUTION

### TEAM A: Click Handler + Socket.IO (45 min total)

| Task | Agent | Priority | Time |
|------|-------|----------|------|
| FileCard onClick → ChatPanel | Sonnet-1 | P0 | 15 min |
| Socket.IO chat_node_update | Sonnet-2 | P0 | 30 min |
| Haiku verify click+events | Haiku-1 | P0 | 10 min |

### TEAM B: Timeline Y-axis (1 hour)

| Task | Agent | Priority | Time |
|------|-------|----------|------|
| Connect calculate_chat_positions() | Sonnet-3 | P1 | 45 min |
| Test Y-axis ordering | Haiku-2 | P1 | 15 min |

### TEAM C: Artifacts Scan (2 hours)

| Task | Agent | Priority | Time |
|------|-------|----------|------|
| Backend: scan data/artifacts/ | Sonnet-4 | P1 | 1 hour |
| Frontend: artifact nodes in tree | Sonnet-5 | P1 | 45 min |
| Link artifacts via message_id | Haiku-3 | P1 | 15 min |

### TEAM D: Markers + Docs (parallel)

| Task | Agent | Priority | Time |
|------|-------|----------|------|
| Mycelium marker placement | Mycelium | P2 | ongoing |
| OpenCode: test coverage | OpenCode | P2 | 30 min |
| Mistral: docs formatting | Mistral | P3 | 20 min |

---

## MARKERS TO ADD (Mycelium)

```
MARKER_108_3_CLICK_HANDLER - FileCard.tsx onClick
MARKER_108_3_SOCKETIO_UPDATE - Socket.IO event handler
MARKER_108_3_TIMELINE_Y - tree_routes.py Y-axis connection
MARKER_108_3_ARTIFACT_SCAN - artifact scanner
MARKER_108_3_ARTIFACT_NODE - frontend artifact rendering
```

---

## SUCCESS CRITERIA

1. Click chat node → opens ChatPanel with messages
2. Socket.IO `chat_node_update` → opacity animates
3. Y-axis: older chats at bottom, newer at top
4. Artifacts from data/artifacts/ appear in tree
5. All 5 markers in place

---

## PARALLEL EXECUTION TIMELINE

```
0:00 ─┬─ TEAM A: Click + Socket.IO starts
      ├─ TEAM D: Mycelium markers parallel
      │
0:15 ─┼─ Click handler done → verify
      │
0:30 ─┼─ TEAM B: Timeline Y-axis starts
      │
0:45 ─┼─ Socket.IO done → verify
      ├─ TEAM C: Artifacts scan starts
      │
1:30 ─┼─ Timeline done → verify
      │
2:30 ─┼─ Artifacts scan done → verify
      │
2:45 ─┴─ COMMIT Phase 108.3
```

---

## COMMANDS FOR VERIFICATION

```bash
# Test click handler
curl localhost:5001/api/chats/{id}/messages

# Test Socket.IO
wscat -c ws://localhost:5001/socket.io/ -x '{"event":"chat_node_update"}'

# Test Y-axis
curl localhost:5001/api/tree/data | jq '.chat_nodes | sort_by(.metadata.last_activity) | .[].visual_hints.layout_hint.expected_y'

# Test artifacts
ls -la data/artifacts/
curl localhost:5001/api/tree/data | jq '.artifact_nodes'
```
