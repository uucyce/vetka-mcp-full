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
const PING_INTERVAL = 30000;

interface MyceliumMessage {
  type: string;
  [key: string]: unknown;
}

export function useMyceliumSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const connect = useCallback(() => {
    // Don't reconnect if already connected
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(MYCELIUM_WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        console.log('[MYCELIUM WS] Connected to', MYCELIUM_WS_URL);

        // Clear reconnect timer
        if (reconnectTimer.current) {
          clearTimeout(reconnectTimer.current);
          reconnectTimer.current = null;
        }

        // Start ping to keep connection alive
        pingTimer.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, PING_INTERVAL);
      };

      ws.onclose = () => {
        setConnected(false);
        if (pingTimer.current) {
          clearInterval(pingTimer.current);
          pingTimer.current = null;
        }
        // Auto-reconnect silently
        reconnectTimer.current = setTimeout(connect, RECONNECT_INTERVAL);
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
      reconnectTimer.current = setTimeout(connect, RECONNECT_INTERVAL);
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
      if (pingTimer.current) {
        clearInterval(pingTimer.current);
        pingTimer.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { connected };
}

export default useMyceliumSocket;
