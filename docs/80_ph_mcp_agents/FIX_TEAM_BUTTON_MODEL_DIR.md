# Phase 80.21: Team Button Opens Model Directory

## Summary
Changed the Team button behavior when a group is active:
- **Before:** Team button opened Group Settings panel
- **After:** Team button opens Model Directory (phone book)

Added a separate Settings button (gear icon) in the Group Active indicator bar for accessing Group Settings.

## Changes Made

### 1. ChatPanel.tsx - Team Button Logic
**Lines:** ~1184-1205

Changed from:
```typescript
if (activeGroupId) {
  // Toggle groupEditMode
  if (activeTab === 'group' && groupEditMode) {
    setGroupEditMode(false);
    setActiveTab('chat');
  } else {
    setGroupEditMode(true);
    setActiveTab('group');
  }
}
```

Changed to:
```typescript
if (activeGroupId) {
  // Phase 80.21: Team button opens Model Directory
  setLeftPanel(leftPanel === 'models' ? 'none' : 'models');
}
```

### 2. ChatPanel.tsx - Settings Button Added
**Location:** Group Active indicator bar (after Group ID copy button)

Added a gear icon button that opens Group Settings:
```typescript
<button
  onClick={() => {
    setGroupEditMode(true);
    setActiveTab('group');
  }}
  title="Group Settings"
>
  <svg> /* gear icon */ </svg>
</button>
```

### 3. GroupCreatorPanel.tsx - Remove Button Styling
**Lines:** ~621-645

Changed from red styling:
```css
border: '1px solid #442',
color: '#844',
/* hover: borderColor: '#844', background: '#221111' */
```

Changed to neutral gray:
```css
border: '1px solid #444',
color: '#666',
/* hover: borderColor: '#666', background: '#1a1a1a' */
```

## Files Modified
- `/client/src/components/chat/ChatPanel.tsx`
- `/client/src/components/chat/GroupCreatorPanel.tsx`

## UI Flow (After Changes)

### When Group is Active:
1. **Team Button (header)** -> Opens/closes Model Directory (left panel)
2. **Settings Button (gear icon in Group Active bar)** -> Opens Group Settings panel
3. **Leave Button** -> Leaves the group

### When Creating New Group:
1. **Team Button** -> Enter/exit group creation mode (unchanged)

## Testing
1. Create or join a group
2. Click Team button in header - should open Model Directory
3. Click gear icon in Group Active bar - should open Group Settings
4. Verify Remove buttons in Group Settings are gray, not red

## Phase Comment
All changes marked with `Phase 80.21` comments for traceability.
