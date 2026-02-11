# Cursor Brief: Phase 131 Wave 3 — RALF Loop + Doctor UI

**Prerequisites:** Wave 1 ✅ (C20A-E), Wave 2 ✅ (C21A-D), Doctor Upgrade ✅ (131.4)
**Date:** 2026-02-10

## Context

Dragon is currently running chat favorites task (myc_6793ebeb).
Doctor triage now has urgency + team choice (131.4).
Pipeline has BMAD gate (131.1) and EvalAgent retry (131.2).

## Wave 3 Tasks

### C23A: RALFloop Status in DevPanel (MEDIUM, 1.5h)
**Marker:** MARKER_C23A

**Problem:** EvalAgent retry is now active (MARKER_131.2) but invisible. User can't see retry attempts, scores, or escalation.

**Solution:** Add RALF metrics to DevPanel pipeline tab.

**Show for each pipeline run:**
```
Pipeline: myc_6793ebeb
├─ Subtask 1: ✅ score=0.85 (attempt 1/3)
├─ Subtask 2: ⚠️ score=0.55 → retry → ✅ score=0.78 (attempt 2/3)
└─ Subtask 3: 🚫 score=0.45 → retry × 3 → escalated
```

**Data source:** Pipeline results have `verifier_feedback` per subtask with `confidence`, `passed`, `retry_count`.

**Files:**
- `client/src/components/panels/DevPanel.tsx` — add RALF metrics section
- Pipeline WebSocket events already stream subtask progress

---

### C23B: Doctor Quick-Actions in Chat UI (HIGH, 2h)
**Marker:** MARKER_C23B

**Problem:** Doctor now sends rich quick-actions (1d/1t/2d/2t/h) but they're just text in group chat. User types "1d" manually.

**Solution:** Render doctor quick-actions as clickable buttons in chat.

**Detection:** When message from agent "doctor" contains backtick-wrapped actions like `` `1d` ``, render as button.

**Button layout:**
```
┌────────────────────────────────────┐
│ 🔴 URGENT — Task tb_xxx (P1)      │
│                                    │
│ [🐉 Dragons] [🏔️ Titans]          │  ← Run now
│ [📋 Queue D] [📋 Queue T] [⏸ Hold]│  ← Queue/Hold
└────────────────────────────────────┘
```

**On click:** Send the action text (e.g., "1d") as user message to group chat.

**Files:**
- `client/src/components/chat/ChatMessage.tsx` or equivalent — render buttons
- Look for existing message rendering patterns (markdown, code blocks)

---

### C23C: Pipeline Artifact Viewer (MEDIUM, 2h)
**Marker:** MARKER_C23C

**Problem:** Dragon generates code in staging mode (auto_write=False). User needs to see what was generated and approve/reject.

**Solution:** Show staged artifacts in DevPanel with approve/reject buttons.

**Data source:**
- `GET /api/tasks/{task_id}/results` — pipeline results with code
- `data/vetka_staging/` — staged files
- Artifact MCP tools: `vetka_list_artifacts`, `vetka_approve_artifact`, `vetka_reject_artifact`

**UI in DevPanel Results tab:**
```
┌────────────────────────────────────┐
│ Artifact: chat_history_manager.py  │
│ Language: Python | 45 lines        │
│ ┌─────────────────────────────────┐│
│ │ def toggle_favorite(self, ...)  ││  ← Code preview
│ │     ...                         ││
│ └─────────────────────────────────┘│
│ [✅ Approve & Write] [❌ Reject]  │
└────────────────────────────────────┘
```

**On Approve:** Call `POST /api/approval/approve` → writes file to disk
**On Reject:** Call `POST /api/approval/reject` with feedback

---

### C23D: Multi-Agent Status Bar (LOW, 1h)
**Marker:** MARKER_C23D

**Problem:** No way to see which agents are working on what.

**Solution:** Small status bar at bottom of DevPanel or main layout.

**Show:**
```
🐉 Dragon: myc_6793ebeb (build) 3/5 subtasks | 🏗️ Cursor: C23B | ⏸ Mistral: idle
```

**Data source:**
- `GET /api/tasks/active-agents` (Cursor's C20C endpoint)
- Pipeline WebSocket for Dragon progress
- Heartbeat status for daemon

---

## Testing

- [ ] C23A: Run pipeline → see RALF retry metrics in DevPanel
- [ ] C23B: @doctor triage → clickable buttons appear in chat
- [ ] C23C: Dragon stages code → artifacts visible in DevPanel → approve writes file
- [ ] C23D: Status bar shows active agents

## Files Index

| File | Action | Marker |
|------|--------|--------|
| client/src/components/panels/DevPanel.tsx | MODIFY | MARKER_C23A, C23D |
| client/src/components/chat/ChatMessage.tsx | MODIFY | MARKER_C23B |
| client/src/components/panels/DevPanel.tsx | MODIFY | MARKER_C23C |
