/**
 * MARKER_154.13A: MiniTasks — compact task list overlay in DAG canvas.
 *
 * Compact: top 5 tasks with status badges.
 * Expanded: full task list with filters (wraps MCCTaskList).
 * Position: top-left.
 *
 * @phase 154
 * @wave 4
 * @status active
 */

import { useEffect } from 'react';
import { MiniWindow } from './MiniWindow';
import { useMCCStore } from '../../store/useMCCStore';
import { MCCTaskList } from './MCCTaskList';
import { NOLAN_PALETTE } from '../../utils/dagLayout';

// Status → dot color
const STATUS_COLOR: Record<string, string> = {
  pending: '#555',
  queued: '#888',
  running: '#e0e0e0',
  done: '#8a8',
  failed: '#a66',
  hold: '#a98',
  cancelled: '#555',
};

// Compact: show top 5 tasks
function TasksCompact() {
  const tasks = useMCCStore(s => s.tasks);
  const summary = useMCCStore(s => s.summary);
  const fetchTasks = useMCCStore(s => s.fetchTasks);
  const selectedTaskId = useMCCStore(s => s.selectedTaskId);
  const selectTask = useMCCStore(s => s.selectTask);

  // Fetch on mount
  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  // Sort: running first, then pending, then done
  const sorted = [...tasks].sort((a, b) => {
    const order: Record<string, number> = { running: 0, queued: 1, pending: 2, hold: 3, done: 4, failed: 5, cancelled: 6 };
    return (order[a.status] ?? 9) - (order[b.status] ?? 9);
  });

  const display = sorted.slice(0, 5);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 2 }}>
      {/* Summary line */}
      <div style={{
        color: NOLAN_PALETTE.textMuted,
        fontSize: 8,
        marginBottom: 2,
        display: 'flex',
        gap: 8,
      }}>
        <span>{summary?.total || tasks.length} tasks</span>
        {(summary?.by_status?.running ?? 0) > 0 && (
          <span style={{ color: '#e0e0e0' }}>▶ {summary!.by_status.running}</span>
        )}
        {(summary?.by_status?.done ?? 0) > 0 && (
          <span style={{ color: '#8a8' }}>✓ {summary!.by_status.done}</span>
        )}
      </div>

      {/* Task list */}
      {display.map(task => (
        <div
          key={task.id}
          onClick={() => selectTask(task.id)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 5,
            padding: '2px 4px',
            borderLeft: task.id === selectedTaskId ? '2px solid #fff' : '2px solid transparent',
            background: task.id === selectedTaskId ? 'rgba(255,255,255,0.05)' : 'transparent',
            cursor: 'pointer',
          }}
        >
          <span
            style={{
              width: 5,
              height: 5,
              borderRadius: '50%',
              background: STATUS_COLOR[task.status] || '#555',
              flexShrink: 0,
            }}
          />
          <span
            style={{
              color: NOLAN_PALETTE.text,
              fontSize: 9,
              flex: 1,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
            title={task.title}
          >
            {task.title}
          </span>
          <span style={{ color: '#444', fontSize: 7, flexShrink: 0 }}>
            {task.status}
          </span>
        </div>
      ))}

      {tasks.length === 0 && (
        <div style={{ color: '#444', fontSize: 9 }}>No tasks yet</div>
      )}

      {tasks.length > 5 && (
        <div style={{ color: '#444', fontSize: 7, marginTop: 'auto' }}>
          +{tasks.length - 5} more — click ↗ to expand
        </div>
      )}
    </div>
  );
}

export function MiniTasks() {
  return (
    <MiniWindow
      windowId="tasks" // MARKER_155.DRAGGABLE.013: Unique ID for position persistence
      title="Tasks"
      icon="📋"
      position="top-left"
      compactWidth={210}
      compactHeight={150}
      compactContent={<TasksCompact />}
      expandedContent={<MCCTaskList />}
    />
  );
}
