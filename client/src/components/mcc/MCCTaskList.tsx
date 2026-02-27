/**
 * ⚠️ DEPRECATED: MCCTaskList
 *
 * MARKER_155.CLEANUP: Component deprecated in Phase 155.
 * MARKER_155A.G25.DEPRECATED_SURFACE_LOCK: forbidden in runtime path.
 * Replaced by MiniTasks floating window in DAG canvas.
 *
 * This file is kept for reference only. Do not use in new code.
 * All functionality migrated to MiniTasks component.
 *
 * @phase 143
 * @status deprecated
 * @replaced_by MiniTasks
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useMCCStore } from '../../store/useMCCStore';
import { useStore } from '../../store/useStore';
import { useDevPanelStore } from '../../store/useDevPanelStore';
import { NOLAN_PALETTE } from '../../utils/dagLayout';
import { TaskFilterBar } from '../panels/TaskFilterBar';
import { TaskEditor } from '../panels/TaskEditor';
import { TaskDrillDown } from '../panels/TaskDrillDown';

// Status dot shapes
const STATUS_COLORS: Record<string, string> = {
  pending: '#555',
  queued: '#888',
  running: '#e0e0e0',
  done: '#8a8',
  failed: '#a66',
  cancelled: '#555',
  hold: '#a98',
};

// Priority brightness (P1=brightest)
const PRIORITY_COLORS: Record<number, string> = {
  1: '#e0e0e0', 2: '#aaa', 3: '#666', 4: '#444', 5: '#2a2a2a',
};

// Format interval
function fmtInterval(s: number): string {
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  return `${Math.floor(s / 3600)}h`;
}

export function MCCTaskList() {
  const {
    tasks, tasksLoading, fetchTasks, addTask, dispatchTask,
    dispatchNext, cancelTask, selectedTaskId, selectTask,
    activePreset,
    activeAgents,
  } = useMCCStore();

  const selectedKey = useStore(s => s.selectedKey);
  const clearSelectedKey = useStore(s => s.clearSelectedKey);
  const taskFilters = useDevPanelStore(s => s.taskFilters);
  const setTaskFilters = useDevPanelStore(s => s.setTaskFilters);

  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);
  const [drillTaskId, setDrillTaskId] = useState<string | null>(null);
  // heartbeat state removed — now in HeartbeatChip (header)

  // MARKER_145.CLEANUP: Fetch on mount + event-driven only — no polling.
  // Was: 30s setInterval alongside event listener = duplicate fetches.
  // Event 'task-board-updated' fires on every board change from backend.
  useEffect(() => {
    fetchTasks();

    const handleBoardUpdate = () => fetchTasks();
    window.addEventListener('task-board-updated', handleBoardUpdate);

    return () => {
      window.removeEventListener('task-board-updated', handleBoardUpdate);
    };
  }, [fetchTasks]);

  // Heartbeat countdown moved to HeartbeatChip — Phase 149.2

  // Add task to queue
  const handleAdd = useCallback(async () => {
    if (!newTaskTitle.trim()) return;
    const preset = activePreset;
    const phaseType = preset.startsWith('titan') ? 'research' : 'build';
    const tags = [preset.startsWith('titan') ? 'titan' : 'dragon'];

    await addTask(newTaskTitle.trim(), preset, phaseType, tags, selectedKey);
    setNewTaskTitle('');
  }, [newTaskTitle, activePreset, addTask, selectedKey]);

  // Dispatch next
  const handleDispatchNext = useCallback(async () => {
    await dispatchNext(selectedKey);
    if (selectedKey) clearSelectedKey();
  }, [dispatchNext, selectedKey, clearSelectedKey]);

  const taskSources = useMemo(() => {
    return Array.from(new Set(tasks.map(t => String(t.source || '')).filter(Boolean))).sort();
  }, [tasks]);

  const taskPresets = useMemo(() => {
    return Array.from(new Set(tasks.map(t => String(t.preset || '')).filter(Boolean))).sort();
  }, [tasks]);

  const filteredTasks = useMemo(() => {
    const q = taskFilters.query.trim().toLowerCase();
    const fromTs = taskFilters.dateFrom ? new Date(`${taskFilters.dateFrom}T00:00:00`).getTime() : null;
    const toTs = taskFilters.dateTo ? new Date(`${taskFilters.dateTo}T23:59:59`).getTime() : null;

    const out = tasks.filter((t) => {
      if (!taskFilters.showCompleted && (t.status === 'done' || t.status === 'failed')) return false;
      if (taskFilters.source !== 'all' && String(t.source || '') !== taskFilters.source) return false;
      if (taskFilters.preset !== 'all' && String(t.preset || '') !== taskFilters.preset) return false;
      if (taskFilters.statuses.length > 0 && !taskFilters.statuses.includes(String(t.status || ''))) return false;

      if (q) {
        const hay = `${t.title || ''} ${t.description || ''}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }

      if (fromTs !== null || toTs !== null) {
        const createdTs = t.created_at ? new Date(t.created_at).getTime() : null;
        if (createdTs !== null) {
          if (fromTs !== null && createdTs < fromTs) return false;
          if (toTs !== null && createdTs > toTs) return false;
        }
      }

      return true;
    });

    const scoreSuccess = (t: any) => Number(t?.stats?.success ? 1 : 0);
    const scoreDuration = (t: any) => Number(t?.stats?.duration_s || 0);
    const scorePriority = (t: any) => Number(t?.priority || 99);
    const scoreCreated = (t: any) => new Date(t?.created_at || 0).getTime();

    out.sort((a: any, b: any) => {
      if (taskFilters.sortBy === 'created_at') return scoreCreated(b) - scoreCreated(a);
      if (taskFilters.sortBy === 'duration_s') return scoreDuration(b) - scoreDuration(a);
      if (taskFilters.sortBy === 'success_rate') return scoreSuccess(b) - scoreSuccess(a);
      return scorePriority(a) - scorePriority(b);
    });
    return out;
  }, [tasks, taskFilters]);

  const pendingCount = tasks.filter(t => t.status === 'pending').length;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        fontFamily: 'monospace',
        fontSize: 10,
        borderRight: `1px solid ${NOLAN_PALETTE.borderDim}`,
        background: '#080808',
      }}
    >
      {/* Quick add */}
      <div style={{ padding: '6px 8px', borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}` }}>
        <div style={{ display: 'flex', gap: 3 }}>
          <input
            type="text"
            placeholder="new task..."
            value={newTaskTitle}
            onChange={e => setNewTaskTitle(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') handleAdd();
            }}
            style={{
              flex: 1,
              background: 'rgba(255,255,255,0.03)',
              border: `1px solid ${NOLAN_PALETTE.borderDim}`,
              borderRadius: 2,
              color: '#ccc',
              padding: '5px 8px',
              fontSize: 10,
              fontFamily: 'monospace',
              outline: 'none',
              minWidth: 0,
            }}
          />
          <button
            onClick={handleAdd}
            disabled={!newTaskTitle.trim()}
            style={{
              background: newTaskTitle.trim() ? 'rgba(255,255,255,0.06)' : 'transparent',
              color: newTaskTitle.trim() ? '#ccc' : '#333',
              border: `1px solid ${NOLAN_PALETTE.borderDim}`,
              borderRadius: 2,
              padding: '4px 6px',
              fontSize: 11,
              cursor: newTaskTitle.trim() ? 'pointer' : 'not-allowed',
              fontWeight: 600,
            }}
            title="Add to queue"
          >+</button>
        </div>
      </div>

      {/* MARKER_152.8: Advanced task filtering/search/sort */}
      <TaskFilterBar
        value={taskFilters}
        sources={taskSources}
        presets={taskPresets}
        onChange={setTaskFilters}
        minimal
      />

      {/* Active agents row */}
      {activeAgents.length > 0 && (
        <div style={{ padding: '4px 8px', borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}` }}>
          {activeAgents.map(agent => (
            <div key={agent.agent_name} style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '2px 0' }}>
              <span style={{
                width: 5, height: 5, borderRadius: '50%',
                background: agent.status === 'running' ? '#e0e0e0' : '#555',
              }} />
              <span style={{ color: '#888', fontSize: 9 }}>{agent.agent_name}</span>
              <span style={{ color: '#555', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 9 }}>
                {agent.task_title?.slice(0, 20)}
              </span>
              <span style={{ color: '#444', fontSize: 8 }}>{fmtInterval(agent.elapsed_seconds)}</span>
            </div>
          ))}
        </div>
      )}

      {/* Task list */}
      <div style={{ flex: 1, overflowY: 'auto', minHeight: 0, padding: '4px 0' }}>
        {tasksLoading && filteredTasks.length === 0 && (
          <div style={{ color: '#555', textAlign: 'center', padding: 16 }}>Loading...</div>
        )}
        {!tasksLoading && filteredTasks.length === 0 && (
          <div style={{ color: '#444', textAlign: 'center', padding: 16, lineHeight: 1.6 }}>
            No tasks yet.<br />
            Use <code style={{ color: '#888' }}>@dragon</code> in chat.
          </div>
        )}
        {filteredTasks.map(task => {
          const isSelected = task.id === selectedTaskId;
          const isRunning = task.status === 'running';
          const isDispatchable = task.status === 'pending' || task.status === 'queued';
          const isEditing = editingTaskId === task.id;
          return (
            <div key={task.id}>
              <div
                onClick={() => selectTask(isSelected ? null : task.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '5px 8px',
                  cursor: 'pointer',
                  background: isSelected ? 'rgba(255,255,255,0.06)' : 'transparent',
                  borderLeft: isSelected ? '2px solid #fff' : '2px solid transparent',
                  transition: 'all 0.1s',
                }}
                onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
                onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
              >
                {/* Priority */}
                <span style={{
                  fontSize: 8, fontWeight: 700, color: '#000',
                  background: PRIORITY_COLORS[task.priority] || '#444',
                  padding: '0px 3px', borderRadius: 1, minWidth: 14, textAlign: 'center',
                }}>P{task.priority}</span>

                {/* Title */}
                <span style={{
                  flex: 1, color: isSelected ? '#fff' : '#ccc', fontSize: 10,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>{task.title}</span>

                {/* Preset badge */}
                {task.preset && (
                  <span style={{ fontSize: 8, color: '#555' }}>
                    {task.preset.replace(/^dragon_/, '').replace(/^titans?_/, 't:').slice(0, 6)}
                  </span>
                )}

                {/* Source chip */}
                {task.source && (
                  <span style={{
                    fontSize: 8,
                    color: '#777',
                    border: '1px solid #2a2a2a',
                    borderRadius: 2,
                    padding: '0 4px',
                    textTransform: 'lowercase',
                    maxWidth: 68,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}>
                    {task.source.replace(/_todo$/, '').slice(0, 10)}
                  </span>
                )}

                {/* Status dot */}
                <span style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: STATUS_COLORS[task.status] || '#555',
                  boxShadow: isRunning ? '0 0 4px rgba(224,224,224,0.4)' : 'none',
                  animation: isRunning ? 'mccPulse 1.5s infinite' : 'none',
                }} />

                {isSelected && (
                  <button
                    onClick={e => {
                      e.stopPropagation();
                      setDrillTaskId(task.id);
                    }}
                    style={{
                      background: 'transparent',
                      color: '#7a7a7a',
                      border: '1px solid #333',
                      borderRadius: 2,
                      padding: '1px 5px',
                      fontSize: 9,
                      cursor: 'pointer',
                      fontFamily: 'monospace',
                    }}
                    title="Task drill-down"
                  >
                    📊
                  </button>
                )}

                {isSelected && (
                  <button
                    onClick={e => {
                      e.stopPropagation();
                      setEditingTaskId(isEditing ? null : task.id);
                    }}
                    style={{
                      background: isEditing ? 'rgba(78,205,196,0.14)' : 'transparent',
                      color: isEditing ? '#bffff9' : '#7a7a7a',
                      border: '1px solid #333',
                      borderRadius: 2,
                      padding: '1px 5px',
                      fontSize: 9,
                      cursor: 'pointer',
                      fontFamily: 'monospace',
                    }}
                    title="Edit task"
                  >
                    ✎
                  </button>
                )}

                {/* Inline actions (on selected) */}
                {isSelected && isDispatchable && (
                  <button
                    onClick={e => { e.stopPropagation(); dispatchTask(task.id, activePreset, selectedKey); }}
                    style={{
                      background: '#2d3d5a', color: '#8af', border: '1px solid #3d4d6a',
                      borderRadius: 2, padding: '1px 5px', fontSize: 9, cursor: 'pointer',
                    }}
                  >▶</button>
                )}
                {isSelected && task.status === 'running' && (
                  <button
                    onClick={e => { e.stopPropagation(); cancelTask(task.id); }}
                    style={{
                      background: 'rgba(160,80,80,0.15)', color: '#c88',
                      border: '1px solid rgba(160,80,80,0.3)',
                      borderRadius: 2, padding: '1px 5px', fontSize: 9, cursor: 'pointer',
                    }}
                  >■</button>
                )}
              </div>
              {isSelected && isEditing && (
                <TaskEditor
                  task={{
                    id: task.id,
                    title: task.title,
                    description: task.description,
                    priority: task.priority,
                    tags: task.tags,
                    source: task.source,
                    source_chat_id: (task as any).source_chat_id,
                    source_group_id: (task as any).source_group_id,
                  }}
                  onSaved={() => {
                    setEditingTaskId(null);
                    fetchTasks();
                  }}
                  onCancel={() => setEditingTaskId(null)}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Footer: dispatch + heartbeat */}
      <div style={{ borderTop: `1px solid ${NOLAN_PALETTE.borderDim}`, padding: '6px 8px' }}>
        <button
          onClick={handleDispatchNext}
          disabled={pendingCount === 0}
          style={{
            width: '100%',
            padding: '7px 0',
            background: pendingCount > 0 ? 'rgba(255,255,255,0.06)' : 'rgba(255,255,255,0.02)',
            color: pendingCount > 0 ? '#e0e0e0' : '#333',
            border: `1px solid ${pendingCount > 0 ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.04)'}`,
            borderRadius: 2,
            fontSize: 9,
            fontFamily: 'monospace',
            fontWeight: 600,
            cursor: pendingCount > 0 ? 'pointer' : 'not-allowed',
            letterSpacing: 2,
            textTransform: 'uppercase',
          }}
        >
          dispatch next {pendingCount > 0 && `(${pendingCount})`}
        </button>

        {/* Heartbeat moved to header HeartbeatChip — Phase 149.2 */}
      </div>

      {/* Pulse animation */}
      <style>{`@keyframes mccPulse { 0%,100%{opacity:1} 50%{opacity:0.4} }`}</style>

      <TaskDrillDown
        isOpen={Boolean(drillTaskId)}
        taskId={drillTaskId}
        onClose={() => setDrillTaskId(null)}
      />
    </div>
  );
}
