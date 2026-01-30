# Phase 82: Group Chat Editing Research & Implementation

Complete research package for adding group editing functionality to VETKA.

## Problem Statement

After creating a group chat in the UI, users have NO editing capabilities:
- Cannot change group name or description
- Cannot modify participant models
- Cannot change participant roles (admin ↔ worker)
- Cannot add/remove participants
- No way to manage the group after creation
- Only option: Leave the group

## Solution Overview

Add a "Settings" button to the group header that opens an editor panel where users can:
1. Change group name and description
2. Change participant models
3. Change participant roles
4. Remove participants
5. Add new participants (future enhancement)

## Documentation Files in This Package

### 1. **GROUP_EDIT_RESEARCH.md** (14KB)
Complete architecture analysis including:
- Current component structure (ChatPanel hierarchy)
- Group state management (where data lives)
- API endpoints (existing + missing)
- Backend group chat manager deep dive
- Socket.IO event system
- Design gaps and implementation roadmap
- Full scope definition

**Read this for:** Understanding the entire system before coding

### 2. **ARCHITECTURE_DIAGRAM.md** (8KB)
Visual ASCII diagrams showing:
- Frontend component tree
- State flow from creation to editing
- Component hierarchy
- Data persistence layers
- Socket.IO events mapping
- Command vs mention system
- Current persistence strategy

**Read this for:** Visual understanding of how components connect

### 3. **CODE_LOCATIONS_REFERENCE.md** (12KB)
Quick lookup guide with:
- Exact line numbers for all relevant code
- Frontend file paths (ChatPanel, GroupCreatorPanel, etc.)
- Backend file paths (group_routes, group_chat_manager, etc.)
- Data class definitions
- Type interfaces
- Testing commands
- Implementation checklist

**Read this for:** Finding specific code and understanding what exists where

### 4. **IMPLEMENTATION_GUIDE.md** (15KB)
Step-by-step implementation guide including:
- 10-step walkthrough (30min - 2hrs per step)
- Complete code snippets for copy-paste
- Backend endpoint implementation (request models + routes)
- GroupChatManager methods (update_group, update_participant)
- Frontend Settings button code
- Complete GroupEditorPanel component
- Testing procedures with curl commands
- Error handling strategies
- Verification checklist

**Read this for:** Actually implementing Phase 82

---

## Quick Start

### For Project Manager/Architect:
1. Read: GROUP_EDIT_RESEARCH.md (sections 1-7)
2. Read: ARCHITECTURE_DIAGRAM.md (overview section)
3. **Result:** Full architecture understood in 20 minutes

### For Backend Developer:
1. Read: CODE_LOCATIONS_REFERENCE.md (Backend section)
2. Read: IMPLEMENTATION_GUIDE.md (Steps 1-3)
3. Follow: Implementation_GUIDE.md step-by-step
4. **Estimate:** 2-3 hours for backend work

### For Frontend Developer:
1. Read: CODE_LOCATIONS_REFERENCE.md (Frontend section)
2. Read: IMPLEMENTATION_GUIDE.md (Steps 4-6)
3. Follow: Implementation_GUIDE.md step-by-step
4. **Estimate:** 3-4 hours for frontend work

### For Full Stack Engineer:
1. Read all documents (1 hour)
2. Follow IMPLEMENTATION_GUIDE.md (8-10 hours)
3. Complete verification checklist

---

## Key Findings

### What Already Exists
- GroupChatManager class with full data model
- All necessary data stored in memory and persisted to JSON
- add_participant() and remove_participant() methods work
- Socket.IO infrastructure for real-time events
- GroupCreatorPanel component (can be adapted)
- Chat history integration for groups

### What's Missing
1. **Backend:** PATCH endpoints for updating group/participants
2. **Backend:** update_group() and update_participant() methods
3. **Frontend:** Settings button in group header
4. **Frontend:** GroupEditorPanel modal component
5. **Optional:** Socket.IO event listeners for real-time updates

### Architecture Assessment
- **Complexity:** LOW - purely additive
- **Risk:** LOW - no changes to existing functionality
- **Dependencies:** NONE - isolated feature
- **Breaking Changes:** NONE - backward compatible
- **Database:** NONE - uses existing JSON file persistence

---

## Implementation Roadmap

### Phase 82 Scope (10-11 hours total)

**Backend (2.5 hours):**
- [ ] Add UpdateGroupRequest model
- [ ] Add UpdateParticipantRequest model
- [ ] Add PATCH /api/groups/{id} endpoint
- [ ] Add PATCH /api/groups/{id}/participants/{agent} endpoint
- [ ] Add GroupChatManager.update_group() method
- [ ] Add GroupChatManager.update_participant() method

**Frontend (4 hours):**
- [ ] Add Settings button to group header
- [ ] Add showGroupEditor state
- [ ] Create GroupEditorPanel component
- [ ] Integrate modal into ChatPanel
- [ ] Add event listeners (optional)

**Testing & Integration (3-4 hours):**
- [ ] Test backend endpoints with curl
- [ ] Test frontend UI flow
- [ ] Integration testing
- [ ] Error handling & edge cases

---

## Success Criteria

Phase 82 is complete when:

1. ✅ Settings button appears in group header
2. ✅ GroupEditorPanel modal opens/closes properly
3. ✅ Can edit group name and description
4. ✅ Can change participant models
5. ✅ Can change participant roles
6. ✅ Changes persist to data/groups.json
7. ✅ Changes visible after reopening group
8. ✅ Group chat messages continue working
9. ✅ No new console errors
10. ✅ All verification tests pass

---

## File Locations

**Backend:**
- Routes: `/src/api/routes/group_routes.py`
- Manager: `/src/services/group_chat_manager.py`
- Data: `data/groups.json`

**Frontend:**
- ChatPanel: `client/src/components/chat/ChatPanel.tsx`
- GroupEditorPanel: `client/src/components/chat/GroupEditorPanel.tsx` (create new)
- GroupCreatorPanel: `client/src/components/chat/GroupCreatorPanel.tsx` (reference)

---

## No New Dependencies Required

All necessary libraries already exist:
- Backend: FastAPI, Pydantic, asyncio
- Frontend: React, Zustand, Lucide icons
- Infrastructure: Socket.IO, JSON persistence

---

## Deployment Considerations

### Backward Compatibility
- Existing groups continue to work unchanged
- New endpoints are additive (no breaking changes)
- No database migrations needed

### Rollout Plan
1. Deploy backend changes first (new endpoints)
2. Deploy frontend changes (UI + component)
3. Monitor for errors
4. Gradual user rollout if needed

---

## Known Limitations (Phase 83+)

1. MCP agent auto-registration not included
2. No offline model validation
3. Last-write-wins for concurrent edits
4. Anyone with access can edit (no role restrictions)

---

**Ready to implement? Start with IMPLEMENTATION_GUIDE.md!**
