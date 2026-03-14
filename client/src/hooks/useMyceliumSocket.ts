/**
 * MARKER_129.C14A: WebSocket hook for MYCELIUM direct connection.
 * DevPanel connects to ws://localhost:8082 for pipeline events.
 * Dispatches same CustomEvents as useSocket.ts — zero changes needed in DevPanel.
 * Graceful fallback: if MYCELIUM unavailable, VETKA SocketIO still works.
 *
 * @status active
 * @phase 129.C14
 * @depends react
 * @used_by DevPanel
 */

import { useEffect, useRef, useState, useCallback } from 'react';

const MYCELIUM_WS_URL = 'ws://localhost:8082';
const RECONNECT_INTERVAL = 5000;

interface MyceliumMessage {
  type: string;
  [key: string]: unknown;
}

export function useMyceliumSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectPendingRef = useRef(false);

  const isWindowActive = useCallback(() => {
    if (typeof document === 'undefined') return true;
    return document.visibilityState === 'visible';
  }, []);

  const connect = useCallback(() => {
    // Don't reconnect if already connected
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(MYCELIUM_WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        console.log('[MYCELIUM WS] Connected to', MYCELIUM_WS_URL);
        reconnectPendingRef.current = false;

        // Clear reconnect timer
        if (reconnectTimer.current) {
          clearTimeout(reconnectTimer.current);
          reconnectTimer.current = null;
        }
      };

      ws.onclose = () => {
        setConnected(false);
        // MARKER_155A.P2.ACTIVE_WINDOW_PRIORITY:
        // Reconnect only when window is active to avoid background churn.
        if (isWindowActive()) {
          reconnectTimer.current = setTimeout(connect, RECONNECT_INTERVAL);
        } else {
          reconnectPendingRef.current = true;
        }
      };

      ws.onerror = () => {
        // Connection failed — MYCELIUM not running, will retry on close
        setConnected(false);
      };

      ws.onmessage = (event) => {
        try {
          const data: MyceliumMessage = JSON.parse(event.data);

          // Dispatch same CustomEvents as useSocket.ts for seamless integration
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
              // Dispatch as both activity and board update
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
              // Heartbeat response, ignore
              break;

            default:
              // Forward raw events for trigger-driven UI refresh flows.
              window.dispatchEvent(new CustomEvent('mycelium-event', { detail: data }));
              if (typeof data.type === 'string') {
                window.dispatchEvent(new CustomEvent(data.type, { detail: data }));
              }
              // Unknown message type — log for debugging
              if (data.type !== 'ping') {
                console.log('[MYCELIUM WS] Unknown message type:', data.type);
              }
          }
        } catch {
          // Ignore malformed messages
        }
      };
    } catch {
      // WebSocket creation failed — MYCELIUM not running
      setConnected(false);
      if (isWindowActive()) {
        reconnectTimer.current = setTimeout(connect, RECONNECT_INTERVAL);
      } else {
        reconnectPendingRef.current = true;
      }
    }
  }, [isWindowActive]);

  useEffect(() => {
    connect();

    const handleWindowActive = () => {
      if (wsRef.current?.readyState === WebSocket.OPEN) return;
      if (!reconnectPendingRef.current && wsRef.current?.readyState === WebSocket.CONNECTING) return;
      reconnectPendingRef.current = false;
      connect();
    };
    document.addEventListener('visibilitychange', handleWindowActive);
    window.addEventListener('focus', handleWindowActive);

    return () => {
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
      document.removeEventListener('visibilitychange', handleWindowActive);
      window.removeEventListener('focus', handleWindowActive);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { connected };
}

export default useMyceliumSocket;
