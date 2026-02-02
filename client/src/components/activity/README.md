# ActivityMonitor Component

**Phase 108.4 Step 5** - Real-time activity feed with Socket.IO integration
**Marker:** `MARKER_108_5_ACTIVITY_UI`

## Features

✅ Fetches from `/api/activity/feed`
✅ Real-time updates via Socket.IO (`activity_update` event)
✅ Filterable by type (chat, mcp, artifact, commit)
✅ Scrollable list with "Load More" pagination
✅ Activity item display with icon, title, and relative timestamp
✅ Expandable details on click
✅ Color-coded left border by activity type
✅ VETKA dark theme styling (#1a1a2e background, #e0e0e0 text)

## Usage

```tsx
import { ActivityMonitor } from './components/activity';

function MyComponent() {
  return (
    <ActivityMonitor
      maxHeight="600px"
      limit={50}
      className="my-custom-class"
    />
  );
}
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `className` | `string` | `''` | Additional CSS class |
| `maxHeight` | `string` | `'500px'` | Max height for scrollable list |
| `limit` | `number` | `50` | Number of activities per page |

## Activity Types

- **💬 chat** - Chat messages (blue border)
- **🔧 mcp** - MCP operations (orange border)
- **📄 artifact** - Artifact operations (purple border)
- **📝 commit** - Git commits (green border)

## Socket.IO Events

The component listens for:
- `activity_update` - Receives new activity items in real-time

## API Endpoints

- `GET /api/activity/feed?limit={limit}&offset={offset}`
  - Returns: `{ activities: Activity[], has_more: boolean }`

## Activity Interface

```typescript
interface Activity {
  id: string;
  type: 'chat' | 'mcp' | 'artifact' | 'commit';
  title: string;
  timestamp: string; // ISO 8601 format
  details?: string; // Shown when expanded
  metadata?: Record<string, any>;
}
```

## Example Activity Object

```json
{
  "id": "act_123",
  "type": "chat",
  "title": "New message in Lightning Chat",
  "timestamp": "2026-02-02T12:15:30Z",
  "details": "User: Hey, can you help me with...",
  "metadata": {
    "chat_id": "609c0d9a-b5bc-426b-b134-d693023bdac8",
    "sender": "danila"
  }
}
```

## Integration Example

### In ChatPanel

```tsx
import { ActivityMonitor } from '../activity';

function ChatPanel() {
  return (
    <div className="chat-panel">
      {/* Existing chat UI */}

      {/* Activity Feed Tab */}
      {activeTab === 'activity' && (
        <ActivityMonitor
          maxHeight="calc(100vh - 200px)"
          limit={100}
        />
      )}
    </div>
  );
}
```

### In Dashboard

```tsx
import { ActivityMonitor } from '../activity';

function Dashboard() {
  return (
    <div className="dashboard">
      <div className="dashboard-widget">
        <h2>Recent Activity</h2>
        <ActivityMonitor maxHeight="400px" limit={20} />
      </div>
    </div>
  );
}
```

## Styling

The component uses VETKA's dark theme palette:
- Background: `#1a1a2e`
- Text: `#e0e0e0`
- Borders: `#333`
- Hover: `rgba(255, 255, 255, 0.03)`

Color-coded borders by type:
- Chat: `#0EA5E9` (blue)
- MCP: `#F59E0B` (orange)
- Artifact: `#8B5CF6` (purple)
- Commit: `#10B981` (green)

## Relative Time Formatting

- `< 1 min` → "just now"
- `< 60 min` → "X min ago"
- `< 24 hours` → "X hour(s) ago"
- `< 7 days` → "X day(s) ago"
- `>= 7 days` → Full date

## Development Notes

- Socket connection is managed per component instance
- Activities are limited to `limit` prop to prevent memory issues
- Automatic cleanup on unmount
- Real-time updates prepend to list and maintain limit
- Smooth scroll with custom scrollbar styling
