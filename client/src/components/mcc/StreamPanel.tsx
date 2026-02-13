/**
 * MARKER_143.P2: StreamPanel — collapsible live pipeline event log.
 * Extracted from MyceliumCommandCenter stream section.
 * Filters by selectedTaskId when a task is focused.
 *
 * @phase 143
 * @status active
 */
import { useMemo } from 'react';
import { useMCCStore } from '../../store/useMCCStore';
import { NOLAN_PALETTE } from '../../utils/dagLayout';

interface StreamPanelProps {
  maxEvents?: number;
}

export function StreamPanel({ maxEvents = 8 }: StreamPanelProps) {
  const streamEvents = useMCCStore(s => s.streamEvents);
  const selectedTaskId = useMCCStore(s => s.selectedTaskId);

  // Filter events by selected task if one is focused
  const filteredEvents = useMemo(() => {
    const events = selectedTaskId
      ? streamEvents.filter(e => !e.taskId || e.taskId === selectedTaskId)
      : streamEvents;
    return events.slice(0, maxEvents);
  }, [streamEvents, selectedTaskId, maxEvents]);

  return (
    <div
      style={{
        borderTop: `1px solid ${NOLAN_PALETTE.borderDim}`,
        background: '#060606',
        padding: '4px 10px',
        flexShrink: 0,
        maxHeight: 72,
        overflowY: 'auto',
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
          fontSize: 9,
          fontFamily: 'monospace',
        }}
      >
        {filteredEvents.length === 0 ? (
          <span style={{ color: NOLAN_PALETTE.textDim, fontSize: 9 }}>
            Waiting for pipeline events...
          </span>
        ) : filteredEvents.map(event => (
          <div key={event.id} style={{ display: 'flex', gap: 6 }}>
            <span style={{ color: '#555', minWidth: 48, fontSize: 8 }}>
              {new Date(event.ts).toLocaleTimeString()}
            </span>
            <span style={{ color: '#777', minWidth: 50, textTransform: 'uppercase', fontSize: 8 }}>
              {event.role}
            </span>
            <span
              style={{
                color: '#bbb',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                flex: 1,
                fontSize: 9,
              }}
              title={event.message}
            >
              {event.message}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
