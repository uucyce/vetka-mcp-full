# Phase 82: Step-by-Step Implementation Guide

Complete walkthrough for adding group editing functionality.

---

## Overview

**Goal:** Enable editing of group chats after creation (name, description, participants, models, roles)

**Scope:**
1. Backend: Add PATCH endpoints for group updates
2. Frontend: Add Settings button + editor panel
3. Integration: Connect UI to API

**Estimate:** 8-10 hours total work

**Risk:** Low - all underlying systems exist, purely additive feature

---

## Step 1: Backend - Add Request Models (30 minutes)

### File: `src/api/routes/group_routes.py`

#### Step 1.1: Add imports (if not present)
```python
from typing import Optional  # Already imported, ensure it's there
```

#### Step 1.2: Add new request models after AddParticipantRequest (after line 34)

```python
class UpdateGroupRequest(BaseModel):
    """Update group metadata."""
    name: Optional[str] = None
    description: Optional[str] = None


class UpdateParticipantRequest(BaseModel):
    """Update participant in group."""
    model_id: Optional[str] = None
    role: Optional[str] = None
    display_name: Optional[str] = None
```

**Location:** Insert after line 34 (after `AddParticipantRequest` class)

**Why:** Pydantic models define what data the API accepts and validates

---

## Step 2: Backend - Add PATCH Endpoints (1 hour)

### File: `src/api/routes/group_routes.py`

#### Step 2.1: Add update group endpoint after remove_participant (after line 118)

```python
@router.patch("/{group_id}")
async def update_group(group_id: str, body: UpdateGroupRequest):
    """Update group metadata (name, description)."""
    manager = get_group_chat_manager()

    # Call manager method (to be implemented in Step 3)
    group = await manager.update_group(group_id, {
        'name': body.name,
        'description': body.description
    })

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    return {'group': group.to_dict()}
```

#### Step 2.2: Add update participant endpoint after update_group

```python
@router.patch("/{group_id}/participants/{agent_id}")
async def update_participant(group_id: str, agent_id: str, body: UpdateParticipantRequest):
    """Update participant metadata (model, role, display_name)."""
    manager = get_group_chat_manager()

    success = await manager.update_participant(
        group_id,
        agent_id,
        {
            'model_id': body.model_id,
            'role': body.role,
            'display_name': body.display_name
        }
    )

    if not success:
        raise HTTPException(status_code=404, detail="Group or participant not found")

    # Return updated participant data
    group = manager.get_group(group_id)
    if group and agent_id in group.get('participants', {}):
        return {'participant': group['participants'][agent_id]}

    raise HTTPException(status_code=404, detail="Participant not found")
```

**Test:**
```bash
# Test update group endpoint
curl -X PATCH http://localhost:8000/api/groups/{group-id} \
  -H "Content-Type: application/json" \
  -d '{"name": "New Name", "description": "New Desc"}'

# Test update participant endpoint
curl -X PATCH http://localhost:8000/api/groups/{group-id}/participants/@PM \
  -H "Content-Type: application/json" \
  -d '{"model_id": "claude-3", "role": "worker"}'
```

---

## Step 3: Backend - Add Manager Methods (1 hour)

### File: `src/services/group_chat_manager.py`

#### Step 3.1: Add update_group method after remove_participant (after line 400)

```python
async def update_group(self, group_id: str, updates: dict) -> Optional[dict]:
    """
    Update group metadata.

    Args:
        group_id: Group ID to update
        updates: Dict with optional keys: 'name', 'description'

    Returns:
        Updated group dict or None if not found
    """
    async with self._lock:
        group = self._groups.get(group_id)
        if not group:
            logger.warning(f"[GroupChat] Cannot update: group not found: {group_id}")
            return None

        # Update fields if provided (ignore None values)
        if updates.get('name') is not None:
            group.name = updates['name']
        if updates.get('description') is not None:
            group.description = updates['description']

        # Update activity timestamp
        group.last_activity = datetime.now()

        # Track LRU activity
        if group_id in self._lru_group_ids:
            self._lru_group_ids.remove(group_id)
        self._lru_group_ids.append(group_id)

    # Emit event for real-time updates
    if self._socketio:
        await self._socketio.emit('group_updated', {
            'group_id': group_id,
            'updates': updates
        })

    # Persist to disk
    await self.save_to_json()

    logger.info(f"[GroupChat] Updated group {group_id}: {updates}")
    return group.to_dict()


async def update_participant(
    self,
    group_id: str,
    agent_id: str,
    updates: dict
) -> bool:
    """
    Update participant metadata.

    Args:
        group_id: Group ID
        agent_id: Participant agent ID (e.g., "@architect")
        updates: Dict with optional keys: 'model_id', 'role', 'display_name'

    Returns:
        True if successful, False if group/participant not found
    """
    async with self._lock:
        group = self._groups.get(group_id)
        if not group:
            logger.warning(f"[GroupChat] Cannot update: group not found: {group_id}")
            return False

        if agent_id not in group.participants:
            logger.warning(f"[GroupChat] Participant not found: {agent_id} in {group_id}")
            return False

        participant = group.participants[agent_id]

        # Update fields if provided (ignore None values)
        if updates.get('model_id') is not None:
            participant.model_id = updates['model_id']

        if updates.get('role') is not None:
            try:
                participant.role = GroupRole(updates['role'])
            except ValueError:
                logger.error(f"[GroupChat] Invalid role: {updates['role']}")
                return False

        if updates.get('display_name') is not None:
            participant.display_name = updates['display_name']

        # Update activity timestamp
        group.last_activity = datetime.now()

        # Track LRU activity
        if group_id in self._lru_group_ids:
            self._lru_group_ids.remove(group_id)
        self._lru_group_ids.append(group_id)

    # Emit event for real-time updates
    if self._socketio:
        await self._socketio.emit('participant_updated', {
            'group_id': group_id,
            'agent_id': agent_id,
            'updates': updates
        })

    # Persist to disk
    await self.save_to_json()

    logger.info(f"[GroupChat] Updated participant {agent_id} in {group_id}: {updates}")
    return True
```

**Why this pattern:**
- Uses existing lock (thread-safe)
- Updates activity timestamp (for LRU tracking)
- Emits socket events (for real-time UI updates)
- Calls save_to_json() (persistent)
- Returns proper status codes

---

## Step 4: Frontend - Add Settings Button (1 hour)

### File: `client/src/components/chat/ChatPanel.tsx`

#### Step 4.1: Add state for editor modal (around line 91, after activeGroupId)

```typescript
// Line ~91 (add after activeGroupId state)
const [showGroupEditor, setShowGroupEditor] = useState(false);
const [editingGroupId, setEditingGroupId] = useState<string | null>(null);
```

#### Step 4.2: Add Settings button to group header (lines 1296-1346)

**Find this section:**
```typescript
{activeGroupId && (
  <div style={{...}}>
    <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#6a8' }} />
    <span style={{ color: '#aaa' }}>Group Active</span>
    <span style={{ color: '#555' }}>|</span>
    <span style={{ color: '#666', fontSize: 10 }}>Use @role to mention</span>
    <button onClick={() => { leaveGroup(activeGroupId); setActiveGroupId(null); }}>
      Leave
    </button>
  </div>
)}
```

**Replace with:**
```typescript
{activeGroupId && (
  <div style={{
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '6px 12px',
    fontSize: 12,
    color: '#888',
    background: '#161616',
    borderRadius: 4,
  }}>
    <span style={{
      width: 6,
      height: 6,
      borderRadius: '50%',
      background: '#6a8'
    }} />
    <span style={{ color: '#aaa' }}>Group Active</span>
    <span style={{ color: '#555' }}>|</span>
    <span style={{ color: '#666', fontSize: 10 }}>Use @role to mention</span>

    {/* NEW: Settings button */}
    <button
      onClick={() => {
        setEditingGroupId(activeGroupId);
        setShowGroupEditor(true);
      }}
      style={{
        marginLeft: 'auto',
        background: 'transparent',
        border: '1px solid #333',
        color: '#666',
        cursor: 'pointer',
        padding: '2px 8px',
        borderRadius: 3,
        fontSize: 10,
        transition: 'all 0.2s'
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = '#555';
        e.currentTarget.style.color = '#aaa';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = '#333';
        e.currentTarget.style.color = '#666';
      }}
    >
      Settings
    </button>

    {/* Existing Leave button */}
    <button
      onClick={() => {
        if (activeGroupId) leaveGroup(activeGroupId);
        setActiveGroupId(null);
        clearChat();
      }}
      style={{
        background: 'transparent',
        border: '1px solid #333',
        color: '#666',
        cursor: 'pointer',
        padding: '2px 8px',
        borderRadius: 3,
        fontSize: 10,
        transition: 'all 0.2s'
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = '#555';
        e.currentTarget.style.color = '#aaa';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = '#333';
        e.currentTarget.style.color = '#666';
      }}
    >
      Leave
    </button>
  </div>
)}
```

---

## Step 5: Frontend - Create GroupEditorPanel Component (2 hours)

### New File: `client/src/components/chat/GroupEditorPanel.tsx`

**Complete implementation:**

```typescript
import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';

interface Participant {
  agent_id: string;
  model_id: string;
  display_name: string;
  role: string;
}

interface GroupData {
  id: string;
  name: string;
  description: string;
  participants: Record<string, Participant>;
}

interface Props {
  groupId: string;
  onClose: () => void;
  onSave: (updates: any) => Promise<void>;
}

const ROLES = ['admin', 'worker', 'reviewer', 'observer'];

export const GroupEditorPanel: React.FC<Props> = ({
  groupId,
  onClose,
  onSave
}) => {
  const [groupData, setGroupData] = useState<GroupData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [participants, setParticipants] = useState<Record<string, Participant>>({});

  // Load group data on mount
  useEffect(() => {
    const loadGroup = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/groups/${groupId}`);
        if (!response.ok) throw new Error('Failed to load group');

        const data = await response.json();
        const group = data.group;

        setGroupData(group);
        setName(group.name);
        setDescription(group.description || '');
        setParticipants(group.participants || {});
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    loadGroup();
  }, [groupId]);

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);

      // 1. Update group metadata if changed
      if (name !== groupData?.name || description !== groupData?.description) {
        await fetch(`/api/groups/${groupId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: name || undefined,
            description: description || undefined
          })
        });
      }

      // 2. Update participants if changed
      if (groupData?.participants) {
        for (const [agentId, newParticipant] of Object.entries(participants)) {
          const oldParticipant = groupData.participants[agentId];

          // Check if anything changed
          const changed =
            newParticipant.model_id !== oldParticipant?.model_id ||
            newParticipant.role !== oldParticipant?.role ||
            newParticipant.display_name !== oldParticipant?.display_name;

          if (changed) {
            await fetch(`/api/groups/${groupId}/participants/${agentId}`, {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                model_id: newParticipant.model_id || undefined,
                role: newParticipant.role || undefined,
                display_name: newParticipant.display_name || undefined
              })
            });
          }
        }
      }

      // Call parent callback
      await onSave({ name, description, participants });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 20, color: '#888', textAlign: 'center' }}>
        Loading group data...
      </div>
    );
  }

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.7)',
          zIndex: 999,
        }}
      />

      {/* Modal */}
      <div style={{
        position: 'fixed',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        background: '#1a1a2e',
        padding: '24px',
        borderRadius: '12px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
        zIndex: 1000,
        width: '600px',
        maxHeight: '80vh',
        overflow: 'auto',
      }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '20px'
        }}>
          <h3 style={{ color: '#fff', margin: 0 }}>Edit Group</h3>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#888',
              cursor: 'pointer',
              fontSize: 20
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Error message */}
        {error && (
          <div style={{
            background: '#8b3a3a',
            color: '#ff6b6b',
            padding: '10px 12px',
            borderRadius: '8px',
            marginBottom: '16px',
            fontSize: '12px'
          }}>
            {error}
          </div>
        )}

        {/* Group Name */}
        <div style={{ marginBottom: '16px' }}>
          <label style={{
            display: 'block',
            fontSize: '10px',
            color: '#666',
            marginBottom: '6px',
            textTransform: 'uppercase'
          }}>
            Group Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{
              width: '100%',
              padding: '10px 12px',
              background: '#2a2a4e',
              border: '1px solid #3a3a5e',
              borderRadius: '8px',
              color: '#fff',
              boxSizing: 'border-box',
              outline: 'none'
            }}
          />
        </div>

        {/* Description */}
        <div style={{ marginBottom: '16px' }}>
          <label style={{
            display: 'block',
            fontSize: '10px',
            color: '#666',
            marginBottom: '6px',
            textTransform: 'uppercase'
          }}>
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            style={{
              width: '100%',
              padding: '10px 12px',
              background: '#2a2a4e',
              border: '1px solid #3a3a5e',
              borderRadius: '8px',
              color: '#fff',
              boxSizing: 'border-box',
              outline: 'none',
              fontFamily: 'inherit',
              minHeight: '80px',
              resize: 'none'
            }}
          />
        </div>

        {/* Participants */}
        <div style={{ marginBottom: '16px' }}>
          <label style={{
            display: 'block',
            fontSize: '10px',
            color: '#666',
            marginBottom: '8px',
            textTransform: 'uppercase'
          }}>
            Participants
          </label>

          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}>
            {Object.entries(participants).map(([agentId, participant]) => (
              <div
                key={agentId}
                style={{
                  display: 'flex',
                  gap: '8px',
                  padding: '10px 12px',
                  background: '#2a2a4e',
                  borderRadius: '8px',
                  alignItems: 'center'
                }}
              >
                {/* Agent name */}
                <div style={{
                  flex: 1,
                  fontSize: '12px',
                  color: '#ccc'
                }}>
                  {participant.display_name}
                </div>

                {/* Model input */}
                <input
                  type="text"
                  value={participant.model_id}
                  onChange={(e) => setParticipants(prev => ({
                    ...prev,
                    [agentId]: { ...prev[agentId], model_id: e.target.value }
                  }))}
                  style={{
                    width: '150px',
                    padding: '6px 8px',
                    background: '#1a1a2e',
                    border: '1px solid #3a3a5e',
                    borderRadius: '4px',
                    color: '#ccc',
                    fontSize: '11px',
                    boxSizing: 'border-box'
                  }}
                  placeholder="model-id"
                />

                {/* Role select */}
                <select
                  value={participant.role}
                  onChange={(e) => setParticipants(prev => ({
                    ...prev,
                    [agentId]: { ...prev[agentId], role: e.target.value }
                  }))}
                  style={{
                    padding: '6px 8px',
                    background: '#1a1a2e',
                    border: '1px solid #3a3a5e',
                    borderRadius: '4px',
                    color: '#ccc',
                    fontSize: '11px'
                  }}
                >
                  {ROLES.map(role => (
                    <option key={role} value={role}>{role}</option>
                  ))}
                </select>

                {/* Remove button */}
                <button
                  onClick={() => {
                    const newParticipants = { ...participants };
                    delete newParticipants[agentId];
                    setParticipants(newParticipants);
                  }}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#666',
                    cursor: 'pointer',
                    padding: '4px 8px'
                  }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Buttons */}
        <div style={{
          display: 'flex',
          gap: '12px',
          marginTop: '20px'
        }}>
          <button
            onClick={handleSave}
            disabled={saving}
            style={{
              flex: 1,
              padding: '12px',
              background: saving ? '#333' : '#4a9eff',
              border: 'none',
              borderRadius: '8px',
              color: '#fff',
              cursor: saving ? 'not-allowed' : 'pointer',
              fontWeight: 500,
              transition: 'background 0.2s',
            }}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>

          <button
            onClick={onClose}
            disabled={saving}
            style={{
              padding: '12px 24px',
              background: 'transparent',
              border: '1px solid #666',
              borderRadius: '8px',
              color: '#999',
              cursor: saving ? 'not-allowed' : 'pointer',
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    </>
  );
};

export default GroupEditorPanel;
```

---

## Step 6: Frontend - Integrate GroupEditorPanel into ChatPanel (1 hour)

### File: `client/src/components/chat/ChatPanel.tsx`

#### Step 6.1: Import GroupEditorPanel (near top with other imports, around line 8)

```typescript
import { GroupEditorPanel } from './GroupEditorPanel';  // Add this line
```

#### Step 6.2: Add modal render before closing tags (around line 1670, before `</>`)

```typescript
{/* Phase 82: Group Editor Modal */}
{showGroupEditor && editingGroupId && (
  <GroupEditorPanel
    groupId={editingGroupId}
    onClose={() => {
      setShowGroupEditor(false);
      setEditingGroupId(null);
    }}
    onSave={async () => {
      // Reload group data if needed
      // For now, changes are persisted immediately by API
    }}
  />
)}
```

---

## Step 7: Testing (1.5 hours)

### Manual Testing Checklist

#### Backend Tests:
```bash
# 1. Create a group first
GROUP_ID=$(curl -s -X POST http://localhost:8000/api/groups \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Group",
    "admin_agent_id": "@PM",
    "admin_model_id": "gpt-4",
    "admin_display_name": "PM"
  }' | jq -r '.group.id')

# 2. Add a participant
curl -X POST http://localhost:8000/api/groups/$GROUP_ID/participants \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "@Dev",
    "model_id": "claude-3",
    "display_name": "Dev",
    "role": "worker"
  }'

# 3. Test PATCH group endpoint
curl -X PATCH http://localhost:8000/api/groups/$GROUP_ID \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Group Name",
    "description": "New description"
  }'

# 4. Verify group was updated
curl -X GET http://localhost:8000/api/groups/$GROUP_ID | jq '.group'

# 5. Test PATCH participant endpoint
curl -X PATCH http://localhost:8000/api/groups/$GROUP_ID/participants/@Dev \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "claude-3-new",
    "role": "admin"
  }'

# 6. Verify participant was updated
curl -X GET http://localhost:8000/api/groups/$GROUP_ID | jq '.group.participants'
```

#### Frontend Tests:
1. Create a group via UI
2. Verify "Settings" button appears
3. Click "Settings" button
4. Modal opens with current group data
5. Edit group name → Save
6. Edit participant model → Save
7. Edit participant role → Save
8. Verify changes appear in UI
9. Close and reopen group → Changes persist
10. Verify messages still work with updated group

#### Integration Tests:
1. Create group
2. Send message
3. Edit group
4. Send another message → should use updated group
5. Leave and rejoin → changes persisted
6. Check data/groups.json → verify on disk

---

## Step 8: Error Handling & Edge Cases (1 hour)

### Add validation in GroupEditorPanel:

```typescript
// Add before handleSave:

const validateChanges = (): string | null => {
  if (!name.trim()) {
    return 'Group name cannot be empty';
  }

  if (Object.keys(participants).length === 0) {
    return 'At least one participant is required';
  }

  return null;
};

// In handleSave, add before trying to save:
const validationError = validateChanges();
if (validationError) {
  setError(validationError);
  return;
}
```

### Handle backend errors:

```typescript
// In handleSave, wrap fetch calls:
try {
  const response = await fetch(`/api/groups/${groupId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({...})
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Update failed');
  }
} catch (err) {
  setError(err instanceof Error ? err.message : 'Unknown error');
  return;
}
```

---

## Step 9: Socket.IO Event Listeners (optional, for real-time)

### Add to ChatPanel.tsx (around line 167 with other event listeners):

```typescript
// Listen for group updates (when other users edit)
useEffect(() => {
  const handleGroupUpdated = (e: CustomEvent) => {
    const data = e.detail;
    if (data.group_id === activeGroupId) {
      // Optionally reload group data or just show notification
      console.log('[ChatPanel] Group updated by another user');
    }
  };

  window.addEventListener('group-updated', handleGroupUpdated as EventListener);
  return () => {
    window.removeEventListener('group-updated', handleGroupUpdated as EventListener);
  };
}, [activeGroupId]);
```

---

## Step 10: Documentation & Cleanup (30 minutes)

### Update inline comments in code:

```typescript
// Phase 82: Group editing support
// Allows users to modify group name, description, participant models/roles
// Connected to PATCH /api/groups/{id} and PATCH /api/groups/{id}/participants/{agent}
```

### Update any README files:

Add to documentation:
- How to edit groups
- What fields can be changed
- Limitations/constraints

---

## Verification Checklist

Before marking Phase 82 complete:

- [ ] Backend PATCH endpoints respond correctly
- [ ] Frontend Settings button appears when group active
- [ ] GroupEditorPanel modal opens/closes properly
- [ ] Can edit group name
- [ ] Can edit group description
- [ ] Can change participant model
- [ ] Can change participant role
- [ ] Can remove participant
- [ ] Changes persist to data/groups.json
- [ ] Changes persist when reopening group
- [ ] Group chat messages continue to work after edits
- [ ] Error messages display properly
- [ ] No console errors
- [ ] Mobile responsive (if applicable)

---

## Common Issues & Fixes

### Issue: Settings button doesn't appear
**Fix:** Check that `activeGroupId !== null` in group header condition

### Issue: Modal won't open
**Fix:** Verify `showGroupEditor` state is being set to true, and GroupEditorPanel is imported

### Issue: Changes not saved
**Fix:** Check browser network tab - verify PATCH requests complete successfully

### Issue: Participants disappear after edit
**Fix:** Ensure participant removal logic only affects intended agent

### Issue: Model dropdown in GroupEditorPanel doesn't work
**Fix:** Verify state update function is correct - use spread operator for immutability

---

## Performance Considerations

1. **Data loading:** GroupEditorPanel fetches fresh data - OK for current scale
2. **Socket.IO:** Optional real-time events - can be added later if needed
3. **Lock usage:** Backend uses asyncio.Lock - prevents race conditions
4. **JSON persistence:** Atomic writes (write to temp, then rename) - safe

---

## Future Enhancements (Phase 83+)

- [ ] MCP agent auto-registration
- [ ] Fine-grained participant permissions
- [ ] Audit log of group changes
- [ ] Group archiving/unarchiving
- [ ] Member invitation system
- [ ] Role templates with preset permissions
- [ ] Group settings (message retention policy, etc.)

---

## Final Verification

### Before pushing to production:

1. All backend tests pass
2. All frontend tests pass
3. Integration tests succeed
4. No new console errors
5. Code is well-commented
6. Error messages are user-friendly
7. Data persistence verified
8. Socket.IO events working (optional)

---

**Phase 82 is complete when all steps are done and verification checklist is green!**
