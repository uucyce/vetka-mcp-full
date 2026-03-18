/**
 * MARKER_154.13A: MiniTasks — compact task list overlay in DAG canvas.
 *
 * MARKER_155E.WF.TASKS_PANEL.MINI_SCROLL_PARITY.V1
 * MARKER_155E.WF.TASKS_PANEL.SELECTION_SYNC_WITH_DAG.V1
 * MARKER_155E.WF.TASKS_PANEL.CONTEXT_ACTIONS.START_STOP.V1
 * MARKER_155E.WF.EXEC.HEARTBEAT_TASK_PANEL_CONTROL.V1
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { MiniWindow } from './MiniWindow';
import { useMCCStore } from '../../store/useMCCStore';
import { NOLAN_PALETTE } from '../../utils/dagLayout';
import type { TaskData } from '../panels/TaskCard';

const STATUS_COLOR: Record<string, string> = {
  pending: '#555',
  queued: '#888',
  running: '#e0e0e0',
  done: '#8a8',
  failed: '#8f948f',
  hold: '#9a9587',
  cancelled: '#555',
};

// MARKER_189.3B: Agent type short labels for compact badge
const AGENT_SHORT: Record<string, string> = {
  claude_code: 'CC',
  cursor: 'Cu',
  mycelium: 'My',
  grok: 'Gk',
  human: 'Hu',
};

// MARKER_189.3A: Project badge color based on project_id hash
function projectColor(pid: string): string {
  if (!pid) return 'transparent';
  let h = 0;
  for (let i = 0; i < pid.length; i++) h = ((h << 5) - h + pid.charCodeAt(i)) | 0;
  const hue = ((h % 360) + 360) % 360;
  return `hsl(${hue}, 35%, 45%)`;
}

const HEARTBEAT_INTERVAL_PRESETS = [
  { label: '10m', value: 600 },
  { label: '30m', value: 1800 },
  { label: '1h', value: 3600 },
  { label: '4h', value: 14400 },
  { label: '1d', value: 86400 },
];

function sortTasks(items: TaskData[]): TaskData[] {
  const order: Record<string, number> = {
    running: 0,
    queued: 1,
    pending: 2,
    hold: 3,
    done: 4,
    failed: 5,
    cancelled: 6,
  };
  return [...items].sort((a, b) => {
    const oa = order[a.status] ?? 99;
    const ob = order[b.status] ?? 99;
    if (oa !== ob) return oa - ob;
    return (b.priority || 99) - (a.priority || 99);
  });
}

function canStartTask(task: TaskData | null | undefined): boolean {
  if (!task) return false;
  return task.status === 'pending' || task.status === 'queued' || task.status === 'hold';
}

function canStopTask(task: TaskData | null | undefined): boolean {
  if (!task) return false;
  return task.status === 'running';
}

function HeartbeatControls({ dense = false }: { dense?: boolean }) {
  const heartbeat = useMCCStore((s) => s.heartbeat);
  const updateHeartbeat = useMCCStore((s) => s.updateHeartbeat);

  if (!heartbeat) return null;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: dense ? '3px 4px' : '5px 6px',
        border: `1px solid ${NOLAN_PALETTE.borderDim}`,
        borderRadius: 4,
        background: 'rgba(255,255,255,0.02)',
      }}
    >
      <span style={{ color: '#8e98a4', fontSize: 8, textTransform: 'uppercase', letterSpacing: 0.4 }}>
        heartbeat
      </span>
      <button
        onClick={() => updateHeartbeat({ enabled: !heartbeat.enabled })}
        style={{
          border: `1px solid ${NOLAN_PALETTE.borderDim}`,
          borderRadius: 3,
          background: heartbeat.enabled ? 'rgba(120,170,120,0.18)' : 'rgba(255,255,255,0.04)',
          color: heartbeat.enabled ? '#b9ddb9' : '#a9b2bc',
          fontSize: 8,
          padding: '1px 6px',
          cursor: 'pointer',
        }}
      >
        {heartbeat.enabled ? 'on' : 'off'}
      </button>
      <select
        value={heartbeat.interval}
        onChange={(e) => updateHeartbeat({ interval: Number(e.target.value) })}
        style={{
          marginLeft: 'auto',
          background: 'rgba(255,255,255,0.03)',
          border: `1px solid ${NOLAN_PALETTE.borderDim}`,
          borderRadius: 3,
          color: '#c6ced8',
          fontSize: 8,
          padding: '1px 4px',
          fontFamily: 'monospace',
        }}
      >
        {HEARTBEAT_INTERVAL_PRESETS.map((preset) => (
          <option key={preset.value} value={preset.value}>{preset.label}</option>
        ))}
      </select>
    </div>
  );
}

function SelectedTaskActions({ selectedTask }: { selectedTask: TaskData | null }) {
  const dispatchTask = useMCCStore((s) => s.dispatchTask);
  const cancelTask = useMCCStore((s) => s.cancelTask);
  const activePreset = useMCCStore((s) => s.activePreset);

  if (!selectedTask) return null;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: '4px 6px',
        border: `1px solid ${NOLAN_PALETTE.borderDim}`,
        borderRadius: 4,
        background: 'rgba(255,255,255,0.03)',
      }}
    >
      <span style={{ color: '#aab3bd', fontSize: 8, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
        active: {selectedTask.title}
      </span>
      {canStartTask(selectedTask) && (
        <button
          onClick={() => dispatchTask(selectedTask.id, activePreset)}
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
          start
        </button>
      )}
      {canStopTask(selectedTask) && (
        <button
          onClick={() => cancelTask(selectedTask.id)}
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
    </div>
  );
}

function TasksCompact() {
  const tasks = useMCCStore((s) => s.tasks);
  const summary = useMCCStore((s) => s.summary);
  const fetchTasks = useMCCStore((s) => s.fetchTasks);
  const selectedTaskId = useMCCStore((s) => s.selectedTaskId);
  const selectTask = useMCCStore((s) => s.selectTask);

  const rowRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const sorted = useMemo(() => sortTasks(tasks), [tasks]);
  const selectedTask = useMemo(() => tasks.find((t) => t.id === selectedTaskId) || null, [tasks, selectedTaskId]);

  useEffect(() => {
    if (!selectedTaskId) return;
    const row = rowRefs.current.get(selectedTaskId);
    if (row) row.scrollIntoView({ block: 'nearest' });
  }, [selectedTaskId, sorted.length]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 4, minHeight: 0 }}>
      <div
        style={{
          color: NOLAN_PALETTE.textMuted,
          fontSize: 8,
          marginBottom: 2,
          display: 'flex',
          gap: 8,
          flexWrap: 'wrap',
        }}
      >
        <span>{summary?.total || tasks.length} tasks</span>
        {(summary?.by_status?.running ?? 0) > 0 && (
          <span style={{ color: '#e0e0e0' }}>▶ {summary!.by_status.running}</span>
        )}
        {(summary?.by_status?.done ?? 0) > 0 && (
          <span style={{ color: '#8a8' }}>✓ {summary!.by_status.done}</span>
        )}
      </div>

      <SelectedTaskActions selectedTask={selectedTask} />

      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2 }}>
        {sorted.map((task) => {
          const selected = task.id === selectedTaskId;
          return (
            <div
              key={task.id}
              ref={(el) => {
                if (el) rowRefs.current.set(task.id, el);
                else rowRefs.current.delete(task.id);
              }}
              onClick={() => selectTask(task.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                padding: '2px 4px',
                borderLeft: selected ? '2px solid #fff' : '2px solid transparent',
                background: selected ? 'rgba(255,255,255,0.05)' : 'transparent',
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
              {/* MARKER_189.3A: project badge */}
              {task.project_id && (
                <span style={{ color: projectColor(task.project_id), fontSize: 6, flexShrink: 0, border: `1px solid ${projectColor(task.project_id)}`, borderRadius: 2, padding: '0 3px', lineHeight: '12px' }}>
                  {task.project_id}
                </span>
              )}
              {/* MARKER_189.3B: agent_type badge */}
              {task.agent_type && (
                <span style={{ color: '#7a7a7a', fontSize: 6, flexShrink: 0, background: 'rgba(255,255,255,0.04)', borderRadius: 2, padding: '0 2px', lineHeight: '12px' }}>
                  {AGENT_SHORT[task.agent_type] || task.agent_type}
                </span>
              )}
              {task.assigned_to && (
                <span style={{ color: '#8d8d8d', fontSize: 7, flexShrink: 0 }}>
                  {task.assigned_to}
                </span>
              )}
              <span style={{ color: '#666', fontSize: 7, flexShrink: 0 }}>{task.status}</span>
            </div>
          );
        })}
        {sorted.length === 0 && (
          <div style={{ color: '#444', fontSize: 9 }}>No tasks yet</div>
        )}
      </div>

      <HeartbeatControls dense />
    </div>
  );
}

function TasksExpanded() {
  const tasks = useMCCStore((s) => s.tasks);
  const selectedTaskId = useMCCStore((s) => s.selectedTaskId);
  const selectTask = useMCCStore((s) => s.selectTask);
  const fetchTasks = useMCCStore((s) => s.fetchTasks);

  const [query, setQuery] = useState('');
  const [status, setStatus] = useState<'all' | 'pending' | 'queued' | 'running' | 'done' | 'failed'>('all');
  const rowRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return sortTasks(
      tasks
        .filter((t) => (status === 'all' ? true : t.status === status))
        .filter((t) => {
          if (!q) return true;
          return `${t.title || ''} ${t.description || ''}`.toLowerCase().includes(q);
        }),
    );
  }, [tasks, query, status]);

  const selectedTask = useMemo(() => tasks.find((t) => t.id === selectedTaskId) || null, [tasks, selectedTaskId]);

  useEffect(() => {
    if (!selectedTaskId) return;
    const row = rowRefs.current.get(selectedTaskId);
    if (row) row.scrollIntoView({ block: 'nearest' });
  }, [selectedTaskId, filtered.length]);

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

      <SelectedTaskActions selectedTask={selectedTask} />
      <HeartbeatControls />

      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 3 }}>
        {filtered.map((task) => {
          const isSelected = task.id === selectedTaskId;
          return (
            <div
              key={task.id}
              ref={(el) => {
                if (el) rowRefs.current.set(task.id, el);
                else rowRefs.current.delete(task.id);
              }}
              onClick={() => selectTask(task.id)}
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
                {/* MARKER_189.3A: project badge (expanded) */}
                {task.project_id && (
                  <span style={{ color: projectColor(task.project_id), fontSize: 7, border: `1px solid ${projectColor(task.project_id)}`, borderRadius: 2, padding: '0 4px', lineHeight: '14px' }}>
                    {task.project_id}{task.project_lane ? `/${task.project_lane}` : ''}
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                <span style={{ color: '#6f6f6f', fontSize: 8 }}>{task.status}</span>
                <span style={{ color: '#555', fontSize: 8 }}>{task.preset || '-'}</span>
                {task.assigned_to && <span style={{ color: '#8d8d8d', fontSize: 8 }}>{task.assigned_to}</span>}
                {task.agent_type && <span style={{ color: '#6a6a6a', fontSize: 8 }}>{task.agent_type}</span>}
                {task.closed_by && <span style={{ color: '#7d7d7d', fontSize: 8 }}>closed:{task.closed_by}</span>}
                {task.source && <span style={{ color: '#575757', fontSize: 8 }}>src:{task.source}</span>}
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
      windowId="tasks"
      title="Tasks"
      icon="📋"
      position="top-left"
      compactWidth={220}
      compactHeight={190}
      compactContent={<TasksCompact />}
      expandedContent={<TasksExpanded />}
    />
  );
}
