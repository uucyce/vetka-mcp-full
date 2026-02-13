/**
 * MARKER_143.P2: MCCTaskList — compact left panel task list.
 * Extracted from DevPanel Board tab into a standalone column component.
 * Tasks are compact (single line) — click to focus, not expand inline.
 *
 * @phase 143
 * @status active
 */
import { useState, useEffect, useCallback } from 'react';
import { useMCCStore } from '../../store/useMCCStore';
import { useStore } from '../../store/useStore';
import { NOLAN_PALETTE } from '../../utils/dagLayout';
import { ArchitectChat } from './ArchitectChat';

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

interface MCCTaskListProps {
  /** MARKER_144.7: Callback when Architect proposes DAG changes user accepts */
  onAcceptArchitectChanges?: (changes: {
    addNodes?: Array<{ type: string; label: string }>;
    removeNodes?: string[];
    addEdges?: Array<{ source: string; target: string; type: string }>;
  }) => void;
}

export function MCCTaskList({ onAcceptArchitectChanges }: MCCTaskListProps = {}) {
  const {
    tasks, tasksLoading, fetchTasks, addTask, dispatchTask,
    dispatchNext, cancelTask, selectedTaskId, selectTask,
    statusFilter, setStatusFilter, activePreset, heartbeat, updateHeartbeat,
    activeAgents,
  } = useMCCStore();

  const selectedKey = useStore(s => s.selectedKey);
  const clearSelectedKey = useStore(s => s.clearSelectedKey);

  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [hbExpanded, setHbExpanded] = useState(false);
  const [nextTickIn, setNextTickIn] = useState<number | null>(null);

  // Fetch on mount + poll + listen for events
  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 30000);

    const handleBoardUpdate = () => fetchTasks();
    window.addEventListener('task-board-updated', handleBoardUpdate);

    return () => {
      clearInterval(interval);
      window.removeEventListener('task-board-updated', handleBoardUpdate);
    };
  }, [fetchTasks]);

  // Heartbeat countdown
  useEffect(() => {
    if (!heartbeat?.enabled || !heartbeat.last_tick) {
      setNextTickIn(null);
      return;
    }
    const update = () => {
      const remaining = Math.max(0, Math.round(heartbeat.last_tick + heartbeat.interval - Date.now() / 1000));
      setNextTickIn(remaining);
    };
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, [heartbeat?.enabled, heartbeat?.last_tick, heartbeat?.interval]);

  // Add & optionally run
  const handleAdd = useCallback(async (andRun: boolean) => {
    if (!newTaskTitle.trim()) return;
    const preset = activePreset;
    const phaseType = preset.startsWith('titan') ? 'research' : 'build';
    const tags = [preset.startsWith('titan') ? 'titan' : 'dragon'];

    const taskId = await addTask(newTaskTitle.trim(), preset, phaseType, tags, selectedKey);
    setNewTaskTitle('');

    if (andRun && taskId) {
      await dispatchTask(taskId, preset, selectedKey);
      if (selectedKey) clearSelectedKey();
    }
  }, [newTaskTitle, activePreset, addTask, dispatchTask, selectedKey, clearSelectedKey]);

  // Dispatch next
  const handleDispatchNext = useCallback(async () => {
    await dispatchNext(selectedKey);
    if (selectedKey) clearSelectedKey();
  }, [dispatchNext, selectedKey, clearSelectedKey]);

  const filteredTasks = tasks.filter(t =>
    statusFilter === 'all' || t.status === statusFilter || (statusFilter === 'done' && t.status === 'failed')
  );

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
              if (e.key === 'Enter') handleAdd(false);
              if (e.key === 'Enter' && e.shiftKey) handleAdd(true);
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
            onClick={() => handleAdd(false)}
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
          <button
            onClick={() => handleAdd(true)}
            disabled={!newTaskTitle.trim()}
            style={{
              background: newTaskTitle.trim() ? '#2d3d5a' : 'transparent',
              color: newTaskTitle.trim() ? '#8af' : '#333',
              border: `1px solid ${newTaskTitle.trim() ? '#3d4d6a' : NOLAN_PALETTE.borderDim}`,
              borderRadius: 2,
              padding: '4px 6px',
              fontSize: 11,
              cursor: newTaskTitle.trim() ? 'pointer' : 'not-allowed',
              fontWeight: 600,
            }}
            title="Add & Run"
          >▶</button>
        </div>
      </div>

      {/* Status filters */}
      <div style={{
        display: 'flex',
        gap: 3,
        padding: '4px 8px',
        borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
      }}>
        {(['all', 'pending', 'running', 'done'] as const).map(f => (
          <button
            key={f}
            onClick={() => setStatusFilter(f)}
            style={{
              padding: '2px 6px',
              background: statusFilter === f ? 'rgba(255,255,255,0.08)' : 'transparent',
              border: `1px solid ${statusFilter === f ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.04)'}`,
              borderRadius: 2,
              color: statusFilter === f ? '#ccc' : '#555',
              fontSize: 9,
              cursor: 'pointer',
            }}
          >{f}</button>
        ))}
      </div>

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
          return (
            <div
              key={task.id}
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

              {/* Status dot */}
              <span style={{
                width: 6, height: 6, borderRadius: '50%',
                background: STATUS_COLORS[task.status] || '#555',
                boxShadow: isRunning ? '0 0 4px rgba(224,224,224,0.4)' : 'none',
                animation: isRunning ? 'mccPulse 1.5s infinite' : 'none',
              }} />

              {/* Inline actions (on hover / selected) */}
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
          );
        })}
      </div>

      {/* MARKER_144.12: Architect Chat — collaborative dialog */}
      <ArchitectChat
        selectedNodeId={selectedTaskId}
        workflowContext={{ nodeCount: tasks.length, edgeCount: 0 }}
        onAcceptChanges={onAcceptArchitectChanges}
      />

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

        {/* Heartbeat compact */}
        <div
          onClick={() => setHbExpanded(!hbExpanded)}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '5px 0', marginTop: 4, cursor: 'pointer', fontSize: 9,
          }}
        >
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: heartbeat?.enabled ? '#6a6' : '#444',
          }} />
          <span style={{ color: '#888' }}>Heartbeat</span>
          <span style={{
            color: heartbeat?.enabled ? '#8a8' : '#666',
            padding: '1px 4px',
            background: heartbeat?.enabled ? 'rgba(100,160,100,0.1)' : 'rgba(255,255,255,0.03)',
            borderRadius: 2, fontSize: 8,
          }}>{heartbeat?.enabled ? 'ON' : 'OFF'}</span>
          <span style={{ flex: 1 }} />
          {heartbeat?.enabled && nextTickIn !== null && (
            <span style={{ color: '#666', fontSize: 8 }}>{fmtInterval(nextTickIn)}</span>
          )}
        </div>

        {hbExpanded && heartbeat && (
          <div style={{ display: 'flex', gap: 6, alignItems: 'center', padding: '4px 0' }}>
            <select
              value={heartbeat.interval}
              onChange={e => { e.stopPropagation(); updateHeartbeat({ interval: parseInt(e.target.value) }); }}
              onClick={e => e.stopPropagation()}
              style={{
                background: '#1a1a1a', border: '1px solid #333', borderRadius: 2,
                color: '#ccc', fontSize: 9, padding: '2px 4px',
              }}
            >
              <option value="60">1m</option>
              <option value="300">5m</option>
              <option value="900">15m</option>
              <option value="3600">1h</option>
              <option value="86400">1d</option>
            </select>
            <button
              onClick={e => { e.stopPropagation(); updateHeartbeat({ enabled: !heartbeat.enabled }); }}
              style={{
                padding: '2px 8px',
                background: heartbeat.enabled ? '#2a3a2a' : '#2a2a2a',
                border: `1px solid ${heartbeat.enabled ? '#3a4a3a' : '#444'}`,
                borderRadius: 2, color: heartbeat.enabled ? '#8a8' : '#888',
                fontSize: 9, cursor: 'pointer',
              }}
            >{heartbeat.enabled ? 'OFF' : 'ON'}</button>
            <span style={{ color: '#666', fontSize: 8 }}>
              ticks:{heartbeat.total_ticks} disp:{heartbeat.tasks_dispatched}
            </span>
          </div>
        )}
      </div>

      {/* Pulse animation */}
      <style>{`@keyframes mccPulse { 0%,100%{opacity:1} 50%{opacity:0.4} }`}</style>
    </div>
  );
}
