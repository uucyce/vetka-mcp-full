/**
 * MARKER_124.2C: TaskCard component for Task Board UI.
 * Displays a single task with priority badge, status chip, and actions.
 *
 * @status active
 * @phase 124.2
 * @depends react
 * @used_by DevPanel
 */

import { useState } from 'react';

export interface TaskData {
  id: string;
  title: string;
  description?: string;
  priority: number;
  status: string;
  phase_type: string;
  preset?: string;
  tags?: string[];
  source?: string;
  created_at?: string;
}

interface TaskCardProps {
  task: TaskData;
  onPriorityChange?: (taskId: string, priority: number) => void;
  onRemove?: (taskId: string) => void;
  onDispatch?: (taskId: string) => void;
}

// Priority colors: P1=red, P2=orange, P3=yellow, P4=blue, P5=gray
const PRIORITY_COLORS: Record<number, string> = {
  1: '#ef4444',
  2: '#f97316',
  3: '#eab308',
  4: '#3b82f6',
  5: '#6b7280',
};

// Status display
const STATUS_DISPLAY: Record<string, { icon: string; color: string }> = {
  pending: { icon: '⏳', color: '#9ca3af' },
  queued: { icon: '📋', color: '#60a5fa' },
  running: { icon: '🔄', color: '#3b82f6' },
  done: { icon: '✅', color: '#22c55e' },
  failed: { icon: '❌', color: '#ef4444' },
  cancelled: { icon: '⛔', color: '#6b7280' },
};

// Phase type icons
const PHASE_ICONS: Record<string, string> = {
  build: '🔨',
  fix: '🔧',
  research: '🔍',
};

export function TaskCard({ task, onPriorityChange, onRemove, onDispatch }: TaskCardProps) {
  const [expanded, setExpanded] = useState(false);

  const prioColor = PRIORITY_COLORS[task.priority] || '#6b7280';
  const statusInfo = STATUS_DISPLAY[task.status] || STATUS_DISPLAY.pending;
  const phaseIcon = PHASE_ICONS[task.phase_type] || '📦';
  const isDispatchable = task.status === 'pending' || task.status === 'queued';

  return (
    <div
      style={{
        padding: '8px 10px',
        marginBottom: 6,
        background: expanded ? '#2a2a2a' : '#1e1e1e',
        borderRadius: 6,
        borderLeft: `3px solid ${prioColor}`,
        cursor: 'pointer',
        transition: 'background 0.15s ease',
      }}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Top row: priority + title + status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {/* Priority badge */}
        <span
          style={{
            background: prioColor,
            color: '#fff',
            fontSize: 10,
            fontWeight: 700,
            padding: '1px 5px',
            borderRadius: 3,
            minWidth: 20,
            textAlign: 'center',
          }}
        >
          P{task.priority}
        </span>

        {/* Phase icon */}
        <span style={{ fontSize: 12 }}>{phaseIcon}</span>

        {/* Title */}
        <span
          style={{
            flex: 1,
            fontSize: 12,
            color: '#e0e0e0',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {task.title}
        </span>

        {/* Status */}
        <span style={{ fontSize: 11, color: statusInfo.color }}>
          {statusInfo.icon}
        </span>
      </div>

      {/* Expanded view */}
      {expanded && (
        <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid #333' }}>
          {/* Description */}
          {task.description && task.description !== task.title && (
            <div style={{ fontSize: 11, color: '#999', marginBottom: 6, lineHeight: 1.4 }}>
              {task.description.slice(0, 200)}
              {task.description.length > 200 && '...'}
            </div>
          )}

          {/* Tags */}
          {task.tags && task.tags.length > 0 && (
            <div style={{ display: 'flex', gap: 4, marginBottom: 6, flexWrap: 'wrap' }}>
              {task.tags.map((tag) => (
                <span
                  key={tag}
                  style={{
                    fontSize: 10,
                    background: '#333',
                    color: '#aaa',
                    padding: '1px 6px',
                    borderRadius: 3,
                  }}
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Meta info */}
          <div style={{ fontSize: 10, color: '#666', marginBottom: 6 }}>
            {task.source && `Source: ${task.source}`}
            {task.preset && ` | Preset: ${task.preset}`}
            {task.created_at && ` | ${new Date(task.created_at).toLocaleTimeString()}`}
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            {/* Priority selector */}
            {onPriorityChange && isDispatchable && (
              <select
                value={task.priority}
                onChange={(e) => {
                  e.stopPropagation();
                  onPriorityChange(task.id, parseInt(e.target.value));
                }}
                onClick={(e) => e.stopPropagation()}
                style={{
                  background: '#333',
                  color: '#ccc',
                  border: '1px solid #444',
                  borderRadius: 3,
                  fontSize: 11,
                  padding: '2px 4px',
                }}
              >
                <option value="1">P1 Critical</option>
                <option value="2">P2 High</option>
                <option value="3">P3 Medium</option>
                <option value="4">P4 Low</option>
                <option value="5">P5 Someday</option>
              </select>
            )}

            {/* Dispatch button */}
            {onDispatch && isDispatchable && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDispatch(task.id);
                }}
                style={{
                  background: '#2563eb',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 3,
                  fontSize: 11,
                  padding: '3px 8px',
                  cursor: 'pointer',
                }}
              >
                ▶ Run
              </button>
            )}

            {/* Remove button */}
            {onRemove && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRemove(task.id);
                }}
                style={{
                  background: 'transparent',
                  color: '#666',
                  border: '1px solid #444',
                  borderRadius: 3,
                  fontSize: 11,
                  padding: '2px 8px',
                  cursor: 'pointer',
                  marginLeft: 'auto',
                }}
              >
                ✕
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
