/**
 * MARKER_127.2A: ActivityLog — Real-time pipeline activity monitor.
 * Listens for 'pipeline-activity' CustomEvent from useSocket.ts.
 * Displays agent progress in Nolan monochrome style.
 *
 * @status active
 * @phase 127.2
 * @depends react
 * @used_by DevPanel
 */

import { useState, useEffect, useRef, useCallback } from 'react';

interface LogEntry {
  id: string;
  timestamp: number;
  role: string;
  model: string;
  message: string;
  subtask_idx: number;
  total: number;
  task_id?: string;
  preset?: string;
}

const MAX_ENTRIES = 100;

// Format timestamp as HH:MM:SS
function formatTime(ts: number): string {
  const date = new Date(ts * 1000);
  return date.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function ActivityLog() {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [followTail, setFollowTail] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  // MARKER_127.2A: Listen for pipeline-activity CustomEvent
  useEffect(() => {
    const handleActivity = (e: CustomEvent) => {
      const detail = e.detail;
      if (!detail) return;

      const entry: LogEntry = {
        id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        timestamp: detail.timestamp || Date.now() / 1000,
        role: detail.role || '@unknown',
        model: detail.model || '',
        message: detail.message || '',
        subtask_idx: detail.subtask_idx || 0,
        total: detail.total || 0,
        task_id: detail.task_id,
        preset: detail.preset,
      };

      setEntries(prev => {
        const next = [entry, ...prev];  // Newest on top
        return next.slice(0, MAX_ENTRIES);  // Ring buffer
      });
    };

    window.addEventListener('pipeline-activity', handleActivity as EventListener);
    return () => {
      window.removeEventListener('pipeline-activity', handleActivity as EventListener);
    };
  }, []);

  // Auto-scroll to top (newest) when followTail is enabled
  useEffect(() => {
    if (followTail && scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [entries, followTail]);

  const handleClear = useCallback(() => {
    setEntries([]);
  }, []);

  if (entries.length === 0) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
      }}>
        {/* Empty state */}
        <div style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#555',
          fontSize: 12,
          fontFamily: 'monospace',
        }}>
          No pipeline activity yet.
        </div>
      </div>
    );
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 8,
        paddingBottom: 8,
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}>
        <div style={{
          color: '#666',
          fontSize: 9,
          fontFamily: 'monospace',
          letterSpacing: 0.5,
          textTransform: 'uppercase',
        }}>
          {entries.length} events
        </div>

        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          {/* Follow toggle */}
          <button
            onClick={() => setFollowTail(!followTail)}
            style={{
              background: followTail ? 'rgba(255,255,255,0.08)' : 'transparent',
              color: followTail ? '#e0e0e0' : '#444',
              border: `1px solid ${followTail ? '#333' : '#222'}`,
              borderRadius: 2,
              padding: '3px 8px',
              fontSize: 9,
              fontFamily: 'monospace',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {followTail ? 'following' : 'paused'}
          </button>

          {/* Clear button */}
          <button
            onClick={handleClear}
            style={{
              background: 'transparent',
              color: '#444',
              border: '1px solid #222',
              borderRadius: 2,
              padding: '3px 8px',
              fontSize: 9,
              fontFamily: 'monospace',
              cursor: 'pointer',
              transition: 'color 0.15s',
            }}
          >
            clear
          </button>
        </div>
      </div>

      {/* Log entries */}
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          overflowX: 'hidden',
          minHeight: 0,
          background: '#111',
          borderRadius: 3,
          padding: 8,
        }}
      >
        {entries.map(entry => (
          <div
            key={entry.id}
            style={{
              display: 'flex',
              gap: 8,
              padding: '4px 0',
              borderBottom: '1px solid rgba(255,255,255,0.03)',
              fontSize: 11,
              fontFamily: 'monospace',
              lineHeight: 1.4,
            }}
          >
            {/* Timestamp */}
            <span style={{ color: '#555', flexShrink: 0, fontSize: 10 }}>
              {formatTime(entry.timestamp)}
            </span>

            {/* Role */}
            <span style={{ color: '#888', flexShrink: 0 }}>
              {entry.role}
            </span>

            {/* Model (if present) */}
            {entry.model && entry.model !== 'system' && (
              <span style={{ color: '#555', flexShrink: 0, fontSize: 10 }}>
                ({entry.model.split('/').pop()})
              </span>
            )}

            {/* Progress indicator */}
            {entry.total > 0 && (
              <span style={{ color: '#444', flexShrink: 0, fontSize: 10 }}>
                [{entry.subtask_idx}/{entry.total}]
              </span>
            )}

            {/* Message */}
            <span style={{
              color: '#e0e0e0',
              flex: 1,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              {entry.message}
            </span>
          </div>
        ))}
      </div>

      {/* Footer: current preset if active */}
      {entries[0]?.preset && (
        <div style={{
          marginTop: 6,
          padding: '4px 8px',
          background: 'rgba(255,255,255,0.02)',
          borderRadius: 2,
          fontSize: 9,
          fontFamily: 'monospace',
          color: '#555',
        }}>
          preset: {entries[0].preset}
        </div>
      )}
    </div>
  );
}
