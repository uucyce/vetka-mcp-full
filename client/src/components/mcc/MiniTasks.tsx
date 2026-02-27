/**
 * MARKER_154.13A: MiniTasks — compact task list overlay in DAG canvas.
 *
 * Compact: top 5 tasks with status badges.
 * Expanded: full task list with filters (native MiniTasks panel).
 * Position: top-left.
 *
 * @phase 154
 * @wave 4
 * @status active
 */

import { useEffect } from 'react';
import { MiniWindow } from './MiniWindow';
import { useMCCStore } from '../../store/useMCCStore';
import { NOLAN_PALETTE } from '../../utils/dagLayout';
import { useMemo, useState } from 'react';

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
          onClick={() => selectTask(task.id === selectedTaskId ? null : task.id)}
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

// MARKER_155A.G25.MINITASKS_EXPANDED_V2:
// Legacy MCCTaskList dependency removed.
// Expanded content is now native MiniTasks panel to keep one-path MCC task UX.
function TasksExpanded() {
  const tasks = useMCCStore(s => s.tasks);
  const selectedTaskId = useMCCStore(s => s.selectedTaskId);
  const selectTask = useMCCStore(s => s.selectTask);
  const dispatchTask = useMCCStore(s => s.dispatchTask);
  const cancelTask = useMCCStore(s => s.cancelTask);
  const activePreset = useMCCStore(s => s.activePreset);
  const fetchTasks = useMCCStore(s => s.fetchTasks);

  const [query, setQuery] = useState('');
  const [status, setStatus] = useState<'all' | 'pending' | 'queued' | 'running' | 'done' | 'failed'>('all');

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return tasks
      .filter((t) => status === 'all' ? true : t.status === status)
      .filter((t) => {
        if (!q) return true;
        return `${t.title || ''} ${t.description || ''}`.toLowerCase().includes(q);
      })
      .sort((a, b) => {
        const order: Record<string, number> = { running: 0, queued: 1, pending: 2, hold: 3, done: 4, failed: 5, cancelled: 6 };
        const oa = order[a.status] ?? 99;
        const ob = order[b.status] ?? 99;
        if (oa !== ob) return oa - ob;
        return (b.priority || 99) - (a.priority || 99);
      });
  }, [tasks, query, status]);

  const statuses: Array<'all' | 'pending' | 'queued' | 'running' | 'done' | 'failed'> = [
    'all', 'pending', 'queued', 'running', 'done', 'failed',
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 6 }}>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="search title/description..."
        style={{
          background: 'rgba(255,255,255,0.03)',
          border: `1px solid ${NOLAN_PALETTE.borderDim}`,
          borderRadius: 3,
          color: '#c9c9c9',
          fontFamily: 'monospace',
          fontSize: 9,
          padding: '6px 8px',
          outline: 'none',
        }}
      />

      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
        {statuses.map((s) => (
          <button
            key={s}
            onClick={() => setStatus(s)}
            style={{
              border: `1px solid ${NOLAN_PALETTE.borderDim}`,
              borderRadius: 3,
              background: status === s ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.03)',
              color: status === s ? '#f2f2f2' : '#8c8c8c',
              padding: '2px 6px',
              fontFamily: 'monospace',
              fontSize: 8,
              cursor: 'pointer',
              textTransform: 'uppercase',
              letterSpacing: 0.4,
            }}
          >
            {s}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 3 }}>
        {filtered.map((task) => {
          const isSelected = task.id === selectedTaskId;
          const canLaunch = task.status === 'pending' || task.status === 'queued';
          const canStop = task.status === 'running';
          return (
            <div
              key={task.id}
              onClick={() => selectTask(task.id === selectedTaskId ? null : task.id)}
              style={{
                border: `1px solid ${isSelected ? '#d9d9d9' : NOLAN_PALETTE.borderDim}`,
                borderRadius: 4,
                background: isSelected ? 'rgba(255,255,255,0.07)' : 'rgba(255,255,255,0.02)',
                padding: '6px 8px',
                cursor: 'pointer',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 5, height: 5, borderRadius: '50%', background: STATUS_COLOR[task.status] || '#555' }} />
                <span
                  style={{
                    color: '#e3e3e3',
                    fontSize: 10,
                    flex: 1,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                  title={task.title}
                >
                  {task.title}
                </span>
                <span style={{ color: '#7b7b7b', fontSize: 8 }}>P{task.priority}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                <span style={{ color: '#6f6f6f', fontSize: 8 }}>{task.status}</span>
                <span style={{ color: '#555', fontSize: 8 }}>{task.preset || '-'}</span>
                <span style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
                  {canLaunch && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        dispatchTask(task.id, activePreset);
                      }}
                      style={{
                        border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                        borderRadius: 3,
                        background: 'rgba(255,255,255,0.08)',
                        color: '#d9d9d9',
                        fontSize: 8,
                        padding: '1px 6px',
                        cursor: 'pointer',
                      }}
                    >
                      launch
                    </button>
                  )}
                  {canStop && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        cancelTask(task.id);
                      }}
                      style={{
                        border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                        borderRadius: 3,
                        background: 'rgba(170,80,80,0.14)',
                        color: '#c88',
                        fontSize: 8,
                        padding: '1px 6px',
                        cursor: 'pointer',
                      }}
                    >
                      stop
                    </button>
                  )}
                </span>
              </div>
            </div>
          );
        })}
        {filtered.length === 0 && (
          <div style={{ color: '#5e5e5e', fontSize: 9, padding: '6px 2px' }}>No tasks for current filter.</div>
        )}
      </div>
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
      expandedContent={<TasksExpanded />}
    />
  );
}
