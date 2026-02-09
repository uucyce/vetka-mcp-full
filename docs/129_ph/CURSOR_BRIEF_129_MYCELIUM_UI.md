# CURSOR BRIEF Phase 129: MYCELIUM DevPanel WebSocket

## Context
We're splitting VETKA into 2 MCP servers. MYCELIUM handles pipelines/tasks.
MYCELIUM will have its own WebSocket server on port 8082 for DevPanel.
DevPanel currently gets `pipeline_activity` and `task_board_updated` from VETKA SocketIO.
With MYCELIUM, DevPanel should connect to `ws://localhost:8082` for these events.

**This task is independent** — you can do it now. The hook will gracefully handle
MYCELIUM being unavailable (fallback to existing VETKA SocketIO which already works).

## C14: useMyceliumSocket Hook + DevPanel Connection (Priority 1)

### Problem
DevPanel gets pipeline data from VETKA SocketIO → freezes when VETKA is blocked by pipeline.
Need a direct WebSocket connection to MYCELIUM (separate process, never blocked).

### How It Currently Works
`client/src/hooks/useSocket.ts` lines 1344-1359:
```typescript
socket.on('task_board_updated', (data) => {
  window.dispatchEvent(new CustomEvent('task-board-updated', { detail: data }));
});
socket.on('pipeline_activity', (data) => {
  window.dispatchEvent(new CustomEvent('pipeline-activity', { detail: data }));
});
```

DevPanel components listen to these CustomEvents:
- `DevPanel.tsx:121` → `task-board-updated` → refreshes task list
- `ActivityLog.tsx:289` → `pipeline-activity` → adds activity entry
- `PipelineStats.tsx:51` → `task-board-updated` → refreshes stats

### What Needs to Change

**1. New file: `client/src/hooks/useMyceliumSocket.ts`**

```typescript
/**
 * MARKER_129.C14: WebSocket hook for MYCELIUM direct connection.
 * DevPanel connects to ws://localhost:8082 for pipeline events.
 * Dispatches same CustomEvents as useSocket.ts — zero changes needed in DevPanel.
 * Graceful fallback: if MYCELIUM unavailable, VETKA SocketIO still works.
 */

import { useEffect, useRef, useState, useCallback } from 'react';

const MYCELIUM_WS_URL = 'ws://localhost:8082';
const RECONNECT_INTERVAL = 5000;
const PING_INTERVAL = 30000;

export function useMyceliumSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null);
  const pingTimer = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    // Don't reconnect if already connected
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(MYCELIUM_WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        console.log('[MYCELIUM WS] Connected');
        // Clear reconnect timer
        if (reconnectTimer.current) {
          clearTimeout(reconnectTimer.current);
          reconnectTimer.current = null;
        }
        // Start ping
        pingTimer.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, PING_INTERVAL);
      };

      ws.onclose = () => {
        setConnected(false);
        if (pingTimer.current) clearInterval(pingTimer.current);
        // Auto-reconnect
        reconnectTimer.current = setTimeout(connect, RECONNECT_INTERVAL);
      };

      ws.onerror = () => {
        setConnected(false);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Dispatch same CustomEvents as useSocket.ts
          switch (data.type) {
            case 'pipeline_activity':
              window.dispatchEvent(
                new CustomEvent('pipeline-activity', { detail: data })
              );
              break;
            case 'task_board_updated':
              window.dispatchEvent(
                new CustomEvent('task-board-updated', { detail: data })
              );
              break;
            case 'pipeline_stats':
              window.dispatchEvent(
                new CustomEvent('pipeline-stats', { detail: data })
              );
              break;
            case 'pipeline_complete':
            case 'pipeline_failed':
              // Also dispatch as board update to refresh task list
              window.dispatchEvent(
                new CustomEvent('task-board-updated', { detail: data })
              );
              window.dispatchEvent(
                new CustomEvent('pipeline-activity', { detail: data })
              );
              break;
            case 'connected':
              console.log('[MYCELIUM WS] Server info:', data);
              break;
            case 'pong':
              break; // Heartbeat response, ignore
          }
        } catch {
          // Ignore malformed messages
        }
      };
    } catch {
      // WebSocket creation failed — MYCELIUM not running
      setConnected(false);
      reconnectTimer.current = setTimeout(connect, RECONNECT_INTERVAL);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (pingTimer.current) clearInterval(pingTimer.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  return { connected };
}
```

**2. Modify: `client/src/components/panels/DevPanel.tsx`**

Add import and connection indicator:

```typescript
// Add import at top
import { useMyceliumSocket } from '../../hooks/useMyceliumSocket';

// Inside DevPanel component, add:
const { connected: myceliumConnected } = useMyceliumSocket();

// In the header area (near the tab bar), add connection indicator:
<div style={{
  display: 'inline-flex',
  alignItems: 'center',
  gap: 4,
  marginLeft: 8,
  fontSize: 10,
  color: myceliumConnected ? '#4a4' : '#666',
  fontFamily: 'monospace',
}}>
  <span style={{
    width: 6,
    height: 6,
    borderRadius: '50%',
    background: myceliumConnected ? '#4a4' : '#444',
    display: 'inline-block',
  }} />
  {myceliumConnected ? 'MYC' : 'MYC'}
</div>
```

### Why It Works With Zero Changes to Other Components
The hook dispatches the EXACT SAME CustomEvents (`pipeline-activity`, `task-board-updated`)
that `useSocket.ts` already dispatches. ActivityLog, PipelineStats, DevPanel — they all
listen to window CustomEvents, not directly to socket. So the data source changes
but consumers don't know or care.

**Fallback:** If MYCELIUM WS is down, the hook just retries every 5s silently.
Meanwhile VETKA SocketIO continues to dispatch the same events (useSocket.ts lines 1344-1359).
When MYCELIUM comes online, DevPanel gets events from BOTH sources — which is fine
(duplicate events are handled by React re-render dedup).

### Markers
- MARKER_129.C14A: useMyceliumSocket hook
- MARKER_129.C14B: DevPanel connection indicator

### Files
- `client/src/hooks/useMyceliumSocket.ts` (NEW, ~100 lines)
- `client/src/components/panels/DevPanel.tsx` (MODIFY, +15 lines)

### Style
- Nolan monochrome (green dot = connected, grey = disconnected)
- "MYC" label, monospace, 10px — minimal
- No toast/alert on disconnect — silent reconnect

### Estimated Effort
- 45 min total
