# H16: ChatPanel UI Structure Map - Header Placement Guide

## Mission Summary
Map the ChatPanel component hierarchy to identify optimal header placement ABOVE pinned files but BELOW search bar, with styling guidelines for non-pinned-file appearance.

---

## 1. RENDER STRUCTURE HIERARCHY

### Main Container: Fixed Position Chat Panel
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx`

**Lines 1349-1369:** Main chat panel container with flex column layout
```
<div (main chat panel)
  position: fixed
  display: flex
  flexDirection: column
  width: chatWidth (default 420px, resizable)
  background: rgba(10, 10, 10, 0.88)
  backdropFilter: blur(8px)
  zIndex: 100
```

### Render Order (Top to Bottom)
1. **Resize Handle** (Lines 1371-1391) - Transparent interactive area
2. **Top Header Section** (Lines ~1463-1844) - AI-Chat header with icons/close
3. **UnifiedSearchBar** (Lines 1846-1867) - Search input component
4. **Chat Header** (Lines 1869-1957) - Editable chat name/context
5. **Pinned Files Section** (Lines 1960-2074) - Pin icon + file chips
6. **Message List** (below)
7. **Message Input** (bottom)

---

## 2. CRITICAL INSERTION POINT: BETWEEN SEARCH & PINNED

### Current Location of Search Bar
**Lines 1846-1867**
```tsx
{(activeTab === 'chat' || activeTab === 'group') && (
  <UnifiedSearchBar
    onSelectResult={handleSearchSelect}
    onPinResult={handleSearchPin}
    onOpenArtifact={(result) => { ... }}
    placeholder="Search code/docs..."
    contextPrefix="vetka/"
    compact={true}
  />
)}
```

### Current Location of Chat Header
**Lines 1869-1957**
```tsx
{(activeTab === 'chat' || activeTab === 'group') && currentChatInfo &&
 !(currentChatInfo.contextType === 'file' && pinnedFileIds.length > 0) && (
  <div style={{
    padding: '6px 12px',
    background: '#0f0f0f',
    borderBottom: '1px solid #222',
  }}>
```

**Key Features:**
- Icon (12x12 SVG) showing context type (folder/group/topic/file)
- Editable chat name display
- Edit icon (clickable handler)
- Close/clear icon

### Current Location of Pinned Files
**Lines 1960-2074**
```tsx
{(activeTab === 'chat' || activeTab === 'group') && pinnedFileIds.length > 0 && (
  <div style={{
    padding: '6px 12px',
    background: '#0f0f0f',
    borderBottom: '1px solid #222',
  }}>
    <div style={{
      display: 'flex',
      flexWrap: 'wrap',
      gap: 6,
      alignItems: 'center',
    }}>
      {/* Pin icon (12x12 SVG) */}
      {/* File chips rendered in loop */}
```

**Pinned File Chip Structure (Lines 1982-2026):**
- Individual container: `background: #1a1a1a`, `border: 1px solid #333`
- File icon (10x10 SVG)
- File name (max-width 80px, truncated)
- Close button (10x10 SVG)
- Shows up to 8 files + "+N more" indicator
- Clear-all button for multiple pins

---

## 3. STYLING PATTERNS FOR HEADER

### Container Wrapper (like Search/Chat Header sections)
```tsx
{/* Conditional render wrapper */}
{(activeTab === 'chat' || activeTab === 'group') && (
  <div style={{
    padding: '6px 12px',
    background: '#0f0f0f',
    borderBottom: '1px solid #222',
  }}>
    {/* Inner content */}
  </div>
)}
```

### Inner Content Pattern (like Chat Header, Lines 1878-1901)
```tsx
<div
  onClick={handleAction}
  style={{
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '4px 10px',
    background: '#1a1a1a',
    border: '1px solid #333',
    borderRadius: 4,
    fontSize: 12,
    color: '#aaa',
    cursor: 'pointer',
    transition: 'all 0.15s',
  }}
  onMouseEnter={(e) => {
    e.currentTarget.style.borderColor = '#555';
    e.currentTarget.style.background = '#222';
  }}
  onMouseLeave={(e) => {
    e.currentTarget.style.borderColor = '#333';
    e.currentTarget.style.background = '#1a1a1a';
  }}
>
  {/* Icon (12x12 SVG with flexShrink: 0) */}
  {/* Text content */}
  {/* Action icons on right (marginLeft: 'auto') */}
</div>
```

---

## 4. COLOR SCHEME & TYPOGRAPHY

### Background Hierarchy
- **Panel background:** `rgba(10, 10, 10, 0.88)` (main container)
- **Section wrapper:** `#0f0f0f` (darker)
- **Clickable elements:** `#1a1a1a` (dark gray)
- **Border color default:** `#333` (subtle)
- **Border color hover:** `#555` (visible)

### Text Hierarchy
- **Main text:** `#aaa` (light gray)
- **Secondary text:** `#888` (medium gray, for pinned files)
- **Icon color default:** `#555` (medium gray, stroked)
- **Icon color hover:** `#fff` (white)
- **Font size:** 12px (headers), 11px (pinned chips), 10px (indicators)

### Interactive Elements
- **Border:** `1px solid #333`
- **Border radius:** `4px`
- **Padding:** `4px 10px` (content), `6px 12px` (wrapper)
- **Gap/spacing:** `6px` (horizontal), varies
- **Hover transition:** `all 0.15s`

---

## 5. ICON PATTERNS

### SVG Icons Used
All icons use inline SVG with these attributes:
```tsx
<svg
  width={size}                    // 12, 10px
  height={size}
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"           // or specific color for hover
  strokeWidth={2}                 // or 1.5 for fine lines
  style={{ flexShrink: 0 }}      // Prevent squishing
  // Additional event handlers
/>
```

### Icon Sizes in Header Sections
- **Container icons:** 12x12px
- **File icons:** 10x10px
- **Action icons (edit/close):** 10x10px
- **Overflow indicator:** uses SVG

---

## 6. PROPOSED HEADER PLACEMENT

### Option A: After Search, Before Chat Header
**Insertion location: Between lines 1867-1868**

Pros:
- Closest to where context info should appear
- Above all pinned content
- Natural flow for user discovery

```tsx
{/* Line 1867: After UnifiedSearchBar closes */}

{/* NEW HEADER GOES HERE */}
{(activeTab === 'chat' || activeTab === 'group') && (
  <div style={{
    padding: '6px 12px',
    background: '#0f0f0f',
    borderBottom: '1px solid #222',
  }}>
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 6,
      padding: '4px 10px',
      background: '#1a1a1a',
      border: '1px solid #333',
      borderRadius: 4,
      fontSize: 12,
      color: '#aaa',
      cursor: 'pointer',
      transition: 'all 0.15s',
    }}>
      {/* Icon */}
      {/* Editable text */}
      {/* Action icons */}
    </div>
  </div>
)}

{/* Line 1869: Chat Header continues */}
{(activeTab === 'chat' || activeTab === 'group') && currentChatInfo &&
 !(currentChatInfo.contextType === 'file' && pinnedFileIds.length > 0) && (
```

### Option B: Replace Chat Header (Consolidate)
**Merge functionality: Lines 1869-1957 with new header**

Pros:
- Single editable context component
- Less screen real estate used
- Cleaner hierarchy

Cons:
- More complex conditional logic
- May break existing functionality

---

## 7. KEY STATE VARIABLES & HANDLERS

### State Variables (from useStore)
```tsx
const pinnedFileIds = useStore((s) => s.pinnedFileIds);  // Line 55
const nodes = useStore((s) => s.nodes);                  // Current nodes tree
const activeTab = useStore((s) => s.activeTab);          // 'chat' | 'group'
const currentChatInfo = useStore((s) => s.currentChatInfo); // Lines 820-837
```

### Current Handler Functions
```tsx
// Line 792-820: Rename chat from header
const handleRenameChatFromHeader = useCallback(async () => {
  if (!currentChatInfo) return;
  // POST to /api/chats/{chatId}/rename with new name
  // Updates Zustand store
}, [currentChatInfo, currentChatId]);

// Line 766: Select result from search
const handleSearchSelect = useCallback((result: SearchResult) => {
  // selectNode(result.id)
}, []);

// Line 779: Pin from search
const handleSearchPin = useCallback((result: SearchResult) => {
  // togglePinFile(result.id)
}, []);
```

---

## 8. CONDITIONAL RENDERING LOGIC

### Visibility Conditions
```tsx
// Always show if:
(activeTab === 'chat' || activeTab === 'group')

// Chat header shows if:
(activeTab === 'chat' || activeTab === 'group') &&
currentChatInfo &&
!(currentChatInfo.contextType === 'file' && pinnedFileIds.length > 0)

// Pinned shows if:
(activeTab === 'chat' || activeTab === 'group') &&
pinnedFileIds.length > 0
```

**Note:** The chat header has logic to hide if it's a file chat AND there are pinned files (to avoid duplication).

---

## 9. FLEX LAYOUT STRUCTURE

### Main Panel Flex Layout
```tsx
display: flex
flexDirection: column    // Vertical stack
// Children stack top-to-bottom:
1. Resize handle (pos absolute, overlay)
2. Header section (flex)
3. Search bar (flex)
4. Chat header (flex)
5. Pinned files (flex)
6. Message list (flex: 1, grows to fill)
7. Message input (flex)
```

### Section Flex Layout (Chat Header, Lines 1878-1956)
```tsx
<div (wrapper)
  display: flex
  flexWrap: wrap
  gap: 6
  alignItems: center
>
  {/* Icon */}
  {/* Content (grows) */}
  {/* Action buttons (flexShrink: 0) */}
</div>
```

---

## 10. IMPLEMENTATION CHECKLIST

For new header component:

- [ ] Render AFTER UnifiedSearchBar (line 1867)
- [ ] Use conditional: `(activeTab === 'chat' || activeTab === 'group')`
- [ ] Apply wrapper style: `padding: 6px 12px`, `background: #0f0f0f`, `borderBottom: 1px solid #222`
- [ ] Use inner container: `flex` layout, background `#1a1a1a`, border `1px solid #333`
- [ ] Add icon (12x12 SVG) with `flexShrink: 0`
- [ ] Make text editable (onClick handler like Line 1879)
- [ ] Add hover states: `borderColor #555`, `background #222`
- [ ] Include close/action icons on right (use `marginLeft: auto`)
- [ ] Avoid styling like pinned files (no chips/truncation)
- [ ] Set `fontSize: 12`, `color: #aaa`
- [ ] Add `transition: all 0.15s` for smooth hover

---

## SUMMARY

**HEADER PLACEMENT:** Between lines 1867-1868 (after UnifiedSearchBar, before Chat Header)

**VISUAL HIERARCHY:**
```
┌─────────────────────────────────────┐
│ Top Header (AI-Chat, icons)         │  ← Lines 1463-1844
├─────────────────────────────────────┤
│ [🔍 Search code/docs...]            │  ← Lines 1846-1867 (SearchBar)
├─────────────────────────────────────┤
│ [NEW HEADER SHOULD GO HERE]          │  ← INSERT LOCATION
├─────────────────────────────────────┤
│ 📌 File1.ts  File2.js  +5            │  ← Lines 1960-2074 (Pinned)
├─────────────────────────────────────┤
│ Message 1                            │  ← MessageList
│ Message 2                            │
│ ...                                  │
├─────────────────────────────────────┤
│ [💬 Type message...]                 │  ← MessageInput
└─────────────────────────────────────┘
```

**STYLING TEMPLATE:** Copy structure from Chat Header (lines 1878-1901) but WITHOUT:
- File icon type detection
- Edit/close icon handlers
- Pinned file chip rendering

**FILE:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx`

---

## Document Metadata
- **Mission:** H16
- **Date:** 2026-01-29
- **Component:** ChatPanel.tsx
- **Status:** Ready for implementation
- **Next Step:** Create editable header component following this specification
