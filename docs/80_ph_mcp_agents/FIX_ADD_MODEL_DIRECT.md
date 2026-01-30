# Phase 80.19: Direct Model Addition to Group Chat

## Problem
Currently, users must assign models to predefined roles (PM, Architect, Dev, QA) when creating group chats.
This forces unnecessary role assignment when user just wants to add a model to chat directly.

## Solution
Add ability to add models directly to group chat without role binding:
- Like solo chat - just pick model and add it
- Auto-generate agent_id from model name
- Default role: "worker"

## Implementation

### 1. Backend: New Endpoint
**File:** `src/api/routes/group_routes.py`

New endpoint: `POST /{group_id}/models/add-direct`

```python
class AddModelDirectRequest(BaseModel):
    model_id: str  # e.g., "deepseek/deepseek-r1:free"
    role: str = "worker"  # Default role

@router.post("/{group_id}/models/add-direct")
async def add_model_direct(group_id: str, body: AddModelDirectRequest):
    """
    Phase 80.19: Add model directly without role slot.
    Auto-generates agent_id from model name.
    """
```

### 2. Agent ID Generation
Extract name from model_id:
- `deepseek/deepseek-r1:free` -> `@deepseek-r1`
- `mcp/claude_code` -> `@claude_code`
- `google/gemma-2-9b-it:free` -> `@gemma-2-9b-it`

### 3. Frontend: ModelDirectory Enhancement
**File:** `client/src/components/ModelDirectory.tsx`

When `isGroupMode=true` and no active role slot:
- Add model directly via new endpoint
- Show "+ Add to Group" button on hover

### 4. Frontend: GroupCreatorPanel Enhancement
**File:** `client/src/components/chat/GroupCreatorPanel.tsx`

Add "Direct Models" section below roles:
- List of directly added models
- Click to add more
- Remove button for each

## API Reference

### Add Model Directly
```
POST /api/groups/{group_id}/models/add-direct
Content-Type: application/json

{
  "model_id": "deepseek/deepseek-r1:free",
  "role": "worker"  // optional, default: "worker"
}
```

Response:
```json
{
  "success": true,
  "participant": {
    "agent_id": "@deepseek-r1",
    "model_id": "deepseek/deepseek-r1:free",
    "role": "worker",
    "display_name": "DeepSeek R1",
    "permissions": ["read", "write"]
  }
}
```

## Files Modified
1. `src/api/routes/group_routes.py` - New endpoint `add_model_direct`
2. `client/src/components/ModelDirectory.tsx` - Added props: `activeGroupId`, `hasActiveSlot`, `onModelAddedDirect`
3. `client/src/components/chat/ChatPanel.tsx` - Pass new props to ModelDirectory
4. `client/src/components/chat/GroupCreatorPanel.tsx` - Updated help text

## Implementation Details

### Backend (`group_routes.py`)
- New Pydantic model `AddModelDirectRequest` with `model_id` and optional `role`
- New endpoint `POST /{group_id}/models/add-direct`
- Auto-generates unique `agent_id` from model name (handles collisions with counter)
- Display name created from model part with title case

### Frontend (`ModelDirectory.tsx`)
- New props: `activeGroupId`, `hasActiveSlot`, `onModelAddedDirect`
- New function `handleAddModelDirect()` that calls API endpoint
- Updated click handler to use direct add when `activeGroupId` exists and no active slot
- Updated footer hint to show different message for direct add mode

### Frontend (`ChatPanel.tsx`)
- Pass `activeGroupId` and `hasActiveSlot` to ModelDirectory
- Pass `onModelAddedDirect` callback that shows system message when model added
- Updated `isGroupMode` logic to include active group case

## Testing
1. Create a group chat with some agents
2. Open Model Directory (phone icon)
3. Click on any model - should add directly to group
4. Toast notification "Added [model] to group" appears
5. System message shows agent_id for @mentioning
6. Test collision: add same model twice, should get @model-1, @model-2

## User Flow
1. User is in active group chat
2. User opens Model Directory
3. Footer says "Click a model to add directly to group"
4. User clicks model -> API call -> model added -> notification
5. User can now @mention the new model
