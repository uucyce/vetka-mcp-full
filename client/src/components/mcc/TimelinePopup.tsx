/**
 * MARKER_183.9B: TimelinePopup — shows pipeline timeline for a task node.
 *
 * Fetched from GET /api/analytics/task/{task_id}.
 * Displays: role bars (architect/coder/verifier) with durations,
 * expandable events list, token/cost summary.
 *
 * Nolan palette: pure grayscale, no color except subtle role tints.
 *
 * @phase 183
 * @task tb_1773606025_29
 * @status active
 */

import { useState, useEffect } from 'react';
import { NOLAN_PALETTE } from '../../utils/dagLayout';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TimelineEvent {
  ts: number;
  role: string;
  event: string;
  detail?: string;
  duration_s?: number;
  subtask_idx?: number;
}

interface AgentStat {
  role: string;
  calls: number;
  tokens_in: number;
  tokens_out: number;
  duration_s: number;
  retries: number;
}

interface TaskAnalytics {
  task_id: string;
  title?: string;
  status?: string;
  preset?: string;
  phase_type?: string;
  total_duration_s?: number;
  timeline_events?: TimelineEvent[];
  agent_stats?: AgentStat[];
  token_summary?: { total_in: number; total_out: number };
}

interface TimelinePopupProps {
  taskId: string;
  taskTitle?: string;
  position?: { x: number; y: number };
  onClose: () => void;
}

// ---------------------------------------------------------------------------
// Role colors (subtle grayscale tints — Nolan style)
// ---------------------------------------------------------------------------

const ROLE_TINT: Record<string, string> = {
  architect: '#aaa',
  coder: '#ddd',
  verifier: '#888',
  researcher: '#bbb',
  scout: '#999',
  pipeline: '#777',
};

function getRoleTint(role: string): string {
  return ROLE_TINT[role] || '#999';
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function RoleBar({ stat }: { stat: AgentStat }) {
  const maxDuration = 120; // scale bar against 2 min max
  const pct = Math.min(100, Math.round((stat.duration_s / maxDuration) * 100));

  return (
    <div style={{ padding: '4px 0' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: 11,
        color: NOLAN_PALETTE.textMuted,
        marginBottom: 2,
      }}>
        <span style={{ color: getRoleTint(stat.role), fontWeight: 500 }}>
          {stat.role}
        </span>
        <span>
          {stat.duration_s.toFixed(1)}s · {stat.calls} call{stat.calls !== 1 ? 's' : ''}
          {stat.retries > 0 && <span style={{ color: NOLAN_PALETTE.textDim }}> · {stat.retries}↻</span>}
        </span>
      </div>
      <div style={{
        height: 3,
        background: NOLAN_PALETTE.borderDim,
        borderRadius: 2,
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%',
          width: `${pct}%`,
          background: getRoleTint(stat.role),
          borderRadius: 2,
          transition: 'width 0.3s ease',
          opacity: 0.7,
        }} />
      </div>
    </div>
  );
}

function EventRow({ event, isExpanded, onToggle }: {
  event: TimelineEvent;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const icon = event.event === 'start' ? '▸' :
    event.event === 'end' ? '▪' :
    event.event === 'fail' ? '✕' :
    event.event === 'retry' ? '↻' : '·';

  return (
    <div>
      <div
        onClick={onToggle}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '3px 0',
          cursor: event.detail ? 'pointer' : 'default',
          fontSize: 11,
        }}
      >
        <span style={{ color: getRoleTint(event.role), width: 12, textAlign: 'center' }}>{icon}</span>
        <span style={{ color: NOLAN_PALETTE.textMuted, fontFamily: 'monospace', fontSize: 10, minWidth: 55 }}>
          {event.role}
        </span>
        <span style={{ color: NOLAN_PALETTE.textDim, fontSize: 10 }}>
          {event.event}
        </span>
        {event.duration_s != null && event.duration_s > 0 && (
          <span style={{ color: NOLAN_PALETTE.textDim, fontSize: 9, marginLeft: 'auto' }}>
            {event.duration_s.toFixed(1)}s
          </span>
        )}
        {event.detail && (
          <span style={{ color: NOLAN_PALETTE.textDim, fontSize: 9 }}>
            {isExpanded ? '▾' : '▸'}
          </span>
        )}
      </div>
      {isExpanded && event.detail && (
        <div style={{
          marginLeft: 20,
          padding: '2px 6px',
          fontSize: 10,
          color: NOLAN_PALETTE.textDim,
          fontFamily: 'monospace',
          background: NOLAN_PALETTE.bg,
          borderLeft: `2px solid ${NOLAN_PALETTE.borderDim}`,
          marginBottom: 2,
        }}>
          {event.detail}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export function TimelinePopup({ taskId, taskTitle, position, onClose }: TimelinePopupProps) {
  const [data, setData] = useState<TaskAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedEvent, setExpandedEvent] = useState<number | null>(null);
  const [showAllEvents, setShowAllEvents] = useState(false);

  // Escape to close
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  // Fetch analytics
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch(`http://localhost:5001/api/analytics/task/${taskId}`)
      .then(res => res.json())
      .then(json => {
        if (cancelled) return;
        if (json.success && json.data) {
          setData(json.data);
        } else {
          setError(json.error || 'No data available');
        }
      })
      .catch(err => {
        if (!cancelled) setError(err.message || 'Network error');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [taskId]);

  const events = data?.timeline_events || [];
  const stats = data?.agent_stats || [];
  const visibleEvents = showAllEvents ? events : events.slice(0, 10);

  // Position: near clicked node or centered
  const popupStyle: React.CSSProperties = position ? {
    position: 'absolute',
    top: position.y,
    left: position.x,
    transform: 'translate(-50%, 8px)',
  } : {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
  };

  return (
    <div
      style={{
        ...popupStyle,
        width: 360,
        maxHeight: '60vh',
        overflowY: 'auto',
        background: 'rgba(10, 10, 10, 0.95)',
        backdropFilter: 'blur(20px)',
        border: `1px solid ${NOLAN_PALETTE.border}`,
        borderRadius: 10,
        padding: '12px 16px',
        zIndex: 900,
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      }}
      onClick={(e) => e.stopPropagation()}
    >
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 8,
        paddingBottom: 6,
        borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
      }}>
        <div>
          <div style={{ color: NOLAN_PALETTE.textMuted, fontSize: 10, letterSpacing: 0.8, textTransform: 'uppercase' }}>
            Pipeline Timeline
          </div>
          <div style={{ color: NOLAN_PALETTE.text, fontSize: 13, fontWeight: 500, marginTop: 1 }}>
            {(taskTitle || taskId).length > 35
              ? (taskTitle || taskId).slice(0, 35) + '…'
              : (taskTitle || taskId)}
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: NOLAN_PALETTE.textDim,
            cursor: 'pointer',
            fontSize: 16,
            padding: 4,
          }}
        >
          ✕
        </button>
      </div>

      {/* Loading / Error states */}
      {loading && (
        <div style={{ color: NOLAN_PALETTE.textDim, fontSize: 11, padding: '16px 0', textAlign: 'center' }}>
          Loading timeline…
        </div>
      )}

      {error && (
        <div style={{ color: NOLAN_PALETTE.textDim, fontSize: 11, padding: '12px 0', textAlign: 'center' }}>
          {error}
        </div>
      )}

      {/* Data loaded */}
      {data && !loading && (
        <>
          {/* Summary row */}
          <div style={{
            display: 'flex',
            gap: 12,
            fontSize: 10,
            color: NOLAN_PALETTE.textMuted,
            marginBottom: 8,
          }}>
            {data.status && (
              <span>{data.status}</span>
            )}
            {data.preset && (
              <span style={{ fontFamily: 'monospace' }}>{data.preset}</span>
            )}
            {data.total_duration_s != null && (
              <span>{data.total_duration_s.toFixed(1)}s total</span>
            )}
            {data.token_summary && (
              <span style={{ marginLeft: 'auto' }}>
                {((data.token_summary.total_in + data.token_summary.total_out) / 1000).toFixed(1)}k tok
              </span>
            )}
          </div>

          {/* Agent role bars */}
          {stats.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div style={{
                color: NOLAN_PALETTE.textDim,
                fontSize: 10,
                letterSpacing: 0.5,
                textTransform: 'uppercase',
                marginBottom: 4,
              }}>
                Agents
              </div>
              {stats.map((stat, i) => (
                <RoleBar key={i} stat={stat} />
              ))}
            </div>
          )}

          {/* Timeline events */}
          {events.length > 0 && (
            <div>
              <div style={{
                color: NOLAN_PALETTE.textDim,
                fontSize: 10,
                letterSpacing: 0.5,
                textTransform: 'uppercase',
                marginBottom: 4,
              }}>
                Events ({events.length})
              </div>
              {visibleEvents.map((ev, i) => (
                <EventRow
                  key={i}
                  event={ev}
                  isExpanded={expandedEvent === i}
                  onToggle={() => setExpandedEvent(expandedEvent === i ? null : i)}
                />
              ))}
              {events.length > 10 && !showAllEvents && (
                <button
                  onClick={() => setShowAllEvents(true)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: NOLAN_PALETTE.textDim,
                    fontSize: 10,
                    cursor: 'pointer',
                    padding: '4px 0',
                    fontFamily: 'inherit',
                  }}
                >
                  Show all {events.length} events…
                </button>
              )}
            </div>
          )}

          {events.length === 0 && stats.length === 0 && (
            <div style={{
              color: NOLAN_PALETTE.textDim,
              fontSize: 11,
              padding: '8px 0',
              textAlign: 'center',
              fontStyle: 'italic',
            }}>
              No timeline data recorded
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default TimelinePopup;
