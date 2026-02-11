/**
 * MARKER_126.0C: DevPanel — Task Board + Stats + League Tester
 * MARKER_126.2B: Style upgrade — Nolan glassmorphism, monospace, no emoji
 * MARKER_128.5B: Quick-add with dispatch ("Add & Run")
 * MARKER_128.7A: Toast notifications on pipeline completion
 * MARKER_128.9A: Keyboard navigation (j/k/Enter/r/a)
 * MARKER_129.C14B: MYCELIUM WebSocket connection indicator
 * MARKER_130.C18A: Agent status row in Board tab
 * MARKER_136.W1A: Removed Activity tab (Wave 1 cleanup)
 * Phase 136: Multi-agent sync.
 *
 * @status active
 * @phase 136
 * @depends FloatingWindow, TaskCard, PipelineStats, ArchitectChat, BalancesPanel, useMyceliumSocket
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { FloatingWindow } from '../artifact/FloatingWindow';
import { useStore } from '../../store/useStore';
import { TaskCard, TaskData } from './TaskCard';
import { PipelineStats } from './PipelineStats';
// MARKER_136.W2B: Replaced LeagueTester with ArchitectChat
import { ArchitectChat } from './ArchitectChat';
import { BalancesPanel } from './BalancesPanel';  // MARKER_126.7
// MARKER_136.W1A: ActivityLog removed (Wave 1 cleanup)
import { WatcherStats } from './WatcherStats';  // MARKER_129.1B
import { ArtifactViewer } from './ArtifactViewer';  // MARKER_C23C
import { AgentStatusBar } from './AgentStatusBar';  // MARKER_C23D
import { useMyceliumSocket } from '../../hooks/useMyceliumSocket';  // MARKER_129.C14B
import { MyceliumCommandCenter } from '../mcc/MyceliumCommandCenter';  // MARKER_135.4B: DAG tab

interface DevPanelProps {
  isOpen?: boolean;
  onClose?: () => void;
  standalone?: boolean;  // MARKER_134.C34C: Standalone mode for MCC window
}

const API_BASE = 'http://localhost:5001/api/debug';

type Tab = 'dag' | 'board' | 'stats' | 'architect' | 'balance' | 'watcher' | 'artifacts';  // MARKER_136.W2B: test→architect

// MARKER_131.C22: Heartbeat settings interface
interface HeartbeatSettings {
  enabled: boolean;
  interval: number;
  last_tick: number;
  total_ticks: number;
  tasks_dispatched: number;
}

// MARKER_131.C22: Format interval for display
function formatInterval(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d`;
  return `${Math.floor(seconds / 604800)}w`;
}

// MARKER_136.W1A: Removed Activity tab (Wave 1 cleanup)
// MARKER_136.W2B: Renamed 'test' → 'architect' (ArchitectChat)
const TABS: { id: Tab; label: string }[] = [
  { id: 'dag', label: 'DAG' },  // MARKER_135.4B: First tab
  { id: 'board', label: 'Board' },
  { id: 'stats', label: 'Stats' },
  { id: 'architect', label: 'Architect' },  // MARKER_136.W2B: Was 'Test'
  { id: 'balance', label: 'Balance' },
  { id: 'watcher', label: 'Watcher' },  // MARKER_129.1B
  { id: 'artifacts', label: 'Artifacts' },  // MARKER_C23C
];

// MARKER_128.7A: Toast notification interface
interface ToastData {
  id: string;
  message: string;
  type: 'success' | 'error';
  taskId?: string;
}

// MARKER_130.C18A: Agent status interface
interface AgentStatus {
  agent_name: string;
  agent_type: string;
  task_id: string;
  task_title: string;
  status: string;
  elapsed_seconds: number;
}

// MARKER_126.0C: Tabbed DevPanel
// MARKER_134.C34C: Added standalone mode for MCC window
export function DevPanel({ isOpen = true, onClose, standalone = false }: DevPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>('dag');  // MARKER_135.4B: DAG default
  // MARKER_134.C34J: Task status filter
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'running' | 'done'>('all');
  const [tasks, setTasks] = useState<TaskData[]>([]);
  const [loading, setLoading] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskTeam, setNewTaskTeam] = useState<'dragon' | 'titan'>('dragon');
  const [newTaskPreset, setNewTaskPreset] = useState<string>('dragon_silver');  // MARKER_128.5B
  const [summary, setSummary] = useState<{ total: number; by_status: Record<string, number> } | null>(null);

  // MARKER_128.7A: Toast state
  const [toasts, setToasts] = useState<ToastData[]>([]);

  // MARKER_130.C18A: Active agents state
  const [activeAgents, setActiveAgents] = useState<AgentStatus[]>([]);

  // MARKER_131.C22: Heartbeat settings state
  const [heartbeat, setHeartbeat] = useState<HeartbeatSettings | null>(null);
  const [heartbeatExpanded, setHeartbeatExpanded] = useState(false);

  // MARKER_136.W1B: Countdown timer for next heartbeat tick
  const [nextTickIn, setNextTickIn] = useState<number | null>(null);

  // MARKER_128.9A: Keyboard navigation state
  const [selectedTaskIdx, setSelectedTaskIdx] = useState<number>(-1);
  const boardRef = useRef<HTMLDivElement>(null);

  // MARKER_129.C14B: MYCELIUM WebSocket connection
  const { connected: myceliumConnected } = useMyceliumSocket();

  // MARKER_126.9C: Get selected key for dispatch (moved before handlers that use it)
  const selectedKey = useStore((s) => s.selectedKey);
  const clearSelectedKey = useStore((s) => s.clearSelectedKey);

  // Fetch tasks from backend
  const fetchTasks = useCallback(async () => {
    if (!isOpen) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/task-board`);
      if (res.ok) {
        const data = await res.json();
        setTasks(data.tasks || []);
        setSummary(data.summary || null);
      }

      // MARKER_130.C18A: Fetch active agents
      const agentsRes = await fetch(`${API_BASE}/task-board/active-agents`);
      if (agentsRes.ok) {
        const agentsData = await agentsRes.json();
        setActiveAgents(agentsData.agents || []);
      }

      // MARKER_131.C22: Fetch heartbeat settings
      const hbRes = await fetch(`${API_BASE}/heartbeat/settings`);
      if (hbRes.ok) {
        const hbData = await hbRes.json();
        if (hbData.success) {
          setHeartbeat(hbData);
        }
      }
    } catch (err) {
      console.error('[TaskBoard] Fetch failed:', err);
    } finally {
      setLoading(false);
    }
  }, [isOpen]);

  // MARKER_131.C22: Update heartbeat settings
  // MARKER_136.W2D: Fixed to use server response properly
  const updateHeartbeat = useCallback(async (updates: Partial<HeartbeatSettings>) => {
    try {
      const res = await fetch(`${API_BASE}/heartbeat/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          // Update with server response values
          setHeartbeat(prev => prev ? {
            ...prev,
            enabled: data.enabled ?? updates.enabled ?? prev.enabled,
            interval: data.interval ?? updates.interval ?? prev.interval,
          } : null);
        }
      }
    } catch (err) {
      console.error('[Heartbeat] Update failed:', err);
    }
  }, []);

  // MARKER_128.7B: Show toast for completed task
  const showToast = useCallback((message: string, type: 'success' | 'error', taskId?: string) => {
    const id = `toast_${Date.now()}`;
    setToasts(prev => [...prev, { id, message, type, taskId }]);
    // Auto-dismiss after 5s
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  }, []);

  // Fetch on open, poll every 30s, and listen for SocketIO updates
  // MARKER_124.3D: Live updates via task-board-updated CustomEvent
  // MARKER_128.7B: Toast on pipeline completion
  useEffect(() => {
    if (!isOpen) return;
    fetchTasks();
    const interval = setInterval(fetchTasks, 30000);

    const handleBoardUpdate = async (e: Event) => {
      const detail = (e as CustomEvent).detail;
      // Check if a task just completed
      if (detail?.task_id && (detail?.status === 'done' || detail?.status === 'failed')) {
        const taskTitle = detail.title || detail.task_id.slice(0, 15);
        const confidence = detail.stats?.verifier_avg_confidence;
        const message = detail.status === 'done'
          ? `Pipeline done: ${taskTitle}${confidence ? ` — ${Math.round(confidence * 100)}%` : ''}`
          : `Pipeline failed: ${taskTitle}`;
        showToast(message, detail.status === 'done' ? 'success' : 'error', detail.task_id);
      }
      fetchTasks();
    };
    window.addEventListener('task-board-updated', handleBoardUpdate);

    return () => {
      clearInterval(interval);
      window.removeEventListener('task-board-updated', handleBoardUpdate);
    };
  }, [isOpen, fetchTasks, showToast]);

  // MARKER_136.W1B: Heartbeat countdown timer
  useEffect(() => {
    if (!heartbeat?.enabled || !heartbeat.last_tick) {
      setNextTickIn(null);
      return;
    }

    const updateCountdown = () => {
      const now = Date.now() / 1000;
      const nextTick = heartbeat.last_tick + heartbeat.interval;
      const remaining = Math.max(0, Math.round(nextTick - now));
      setNextTickIn(remaining);
    };

    updateCountdown();
    const timer = setInterval(updateCountdown, 1000);
    return () => clearInterval(timer);
  }, [heartbeat?.enabled, heartbeat?.last_tick, heartbeat?.interval]);

  // Add task
  const handleAddTask = useCallback(async (andRun: boolean = false) => {
    if (!newTaskTitle.trim()) return;

    try {
      // MARKER_128.5B: Use selected preset
      const preset = newTaskTeam === 'titan' ? 'titan_core' : newTaskPreset;

      const res = await fetch(`${API_BASE}/task-board/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newTaskTitle.trim(),
          phase_type: newTaskTeam === 'titan' ? 'research' : 'build',
          preset: preset,
          tags: [newTaskTeam],
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setNewTaskTitle('');

        // MARKER_128.5B: If "Add & Run", dispatch immediately
        if (andRun && data.task_id) {
          await fetch(`${API_BASE}/task-board/dispatch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              task_id: data.task_id,
              preset: preset,
              selected_key: selectedKey,
            }),
          });
          if (selectedKey) clearSelectedKey();
        }

        fetchTasks();
      }
    } catch (err) {
      console.error('[TaskBoard] Add failed:', err);
    }
  }, [newTaskTitle, newTaskTeam, newTaskPreset, fetchTasks, selectedKey, clearSelectedKey]);

  // Update task priority
  const handlePriorityChange = useCallback(async (taskId: string, priority: number) => {
    try {
      await fetch(`${API_BASE}/task-board/${taskId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ priority }),
      });
      fetchTasks();
    } catch (err) {
      console.error('[TaskBoard] Priority update failed:', err);
    }
  }, [fetchTasks]);

  // Remove task
  const handleRemove = useCallback(async (taskId: string) => {
    try {
      await fetch(`${API_BASE}/task-board/${taskId}`, { method: 'DELETE' });
      fetchTasks();
    } catch (err) {
      console.error('[TaskBoard] Remove failed:', err);
    }
  }, [fetchTasks]);

  // MARKER_126.5G: Cancel running task
  const handleCancelTask = useCallback(async (taskId: string) => {
    try {
      await fetch(`${API_BASE}/task-board/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: taskId }),
      });
      fetchTasks();
    } catch (err) {
      console.error('[TaskBoard] Cancel failed:', err);
    }
  }, [fetchTasks]);

  // MARKER_128.5A: Dispatch specific task with optional preset override
  const handleDispatchTask = useCallback(async (taskId: string, preset?: string) => {
    try {
      // MARKER_126.9C: Include selected_key in dispatch request
      // MARKER_128.5A: Include preset if provided
      await fetch(`${API_BASE}/task-board/dispatch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: taskId,
          selected_key: selectedKey,
          ...(preset && { preset }),
        }),
      });
      // Clear key selection after dispatch (one-shot use)
      if (selectedKey) clearSelectedKey();
      fetchTasks();
    } catch (err) {
      console.error('[TaskBoard] Dispatch failed:', err);
    }
  }, [fetchTasks, selectedKey, clearSelectedKey]);

  // Dispatch next (highest priority)
  const handleDispatchNext = useCallback(async () => {
    try {
      // MARKER_126.9C: Include selected_key in dispatch request
      await fetch(`${API_BASE}/task-board/dispatch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          selected_key: selectedKey,
        }),
      });
      // Clear key selection after dispatch (one-shot use)
      if (selectedKey) clearSelectedKey();
      fetchTasks();
    } catch (err) {
      console.error('[TaskBoard] Dispatch next failed:', err);
    }
  }, [fetchTasks, selectedKey, clearSelectedKey]);

  // MARKER_128.9A: Keyboard navigation for Board tab
  useEffect(() => {
    if (!isOpen || activeTab !== 'board') return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle if board is focused (not typing in input)
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      switch (e.key) {
        case 'j': // Move down
          e.preventDefault();
          setSelectedTaskIdx(prev => Math.min(prev + 1, tasks.length - 1));
          break;
        case 'k': // Move up
          e.preventDefault();
          setSelectedTaskIdx(prev => Math.max(prev - 1, 0));
          break;
        case 'Enter': // Expand selected (handled in TaskCard via selectedTaskIdx)
          if (selectedTaskIdx >= 0 && selectedTaskIdx < tasks.length) {
            e.preventDefault();
            // Dispatch custom event to expand task
            window.dispatchEvent(new CustomEvent('task-expand', { detail: { taskId: tasks[selectedTaskIdx].id } }));
          }
          break;
        case 'r': // Run selected task
          if (selectedTaskIdx >= 0 && selectedTaskIdx < tasks.length) {
            const task = tasks[selectedTaskIdx];
            if (task.status === 'pending' || task.status === 'queued') {
              e.preventDefault();
              handleDispatchTask(task.id);
            }
          }
          break;
        case 'a': // Apply all results
          if (selectedTaskIdx >= 0 && selectedTaskIdx < tasks.length) {
            const task = tasks[selectedTaskIdx];
            if (task.status === 'done' || task.status === 'failed') {
              e.preventDefault();
              window.dispatchEvent(new CustomEvent('task-apply-all', { detail: { taskId: task.id } }));
            }
          }
          break;
        case 'Escape':
          setSelectedTaskIdx(-1);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, activeTab, tasks, selectedTaskIdx, handleDispatchTask]);

  if (!isOpen) return null;

  const pendingCount = tasks.filter(t => t.status === 'pending').length;
  const runningCount = tasks.filter(t => t.status === 'running').length;
  const holdCount = tasks.filter(t => t.status === 'hold').length;

  // MARKER_134.C34E: Standalone mode renders without FloatingWindow wrapper
  const content = (
    <>
      {/* Tab bar — Nolan monochrome, monospace */}
      <div style={{
        display: 'flex',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        padding: '0 12px',
        background: 'rgba(0,0,0,0.2)',
      }}>
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              flex: 1,
              padding: '10px 0',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === tab.id ? '1px solid #e0e0e0' : '1px solid transparent',
              color: activeTab === tab.id ? '#e0e0e0' : '#444',
              fontSize: 10,
              fontFamily: 'monospace',
              fontWeight: activeTab === tab.id ? 600 : 400,
              letterSpacing: 1.5,
              textTransform: 'uppercase',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            {tab.label}
          </button>
        ))}

        {/* MARKER_129.C14B: MYCELIUM connection indicator */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            padding: '0 8px',
            fontSize: 9,
            color: myceliumConnected ? '#4a4' : '#444',
            fontFamily: 'monospace',
            letterSpacing: 0.5,
          }}
          title={myceliumConnected ? 'MYCELIUM connected' : 'MYCELIUM disconnected'}
        >
          <span
            style={{
              width: 5,
              height: 5,
              borderRadius: '50%',
              background: myceliumConnected ? '#4a4' : '#333',
            }}
          />
          MYC
        </div>
      </div>

      <div style={{
        padding: 12,
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100% - 36px)',
        color: '#e0e0e0',
        fontSize: 13,
      }}>
        {/* ═══ DAG TAB ═══ */}
        {/* MARKER_135.4B: DAG visualization tab */}
        {activeTab === 'dag' && (
          <div style={{ flex: 1, minHeight: 0, margin: -12, marginTop: -12 }}>
            <MyceliumCommandCenter />
          </div>
        )}

        {/* ═══ BOARD TAB ═══ */}
        {activeTab === 'board' && (
          <>
            {/* Header summary — monospace counters */}
            <div style={{ color: '#444', fontSize: 9, marginBottom: 8, display: 'flex', justifyContent: 'space-between', fontFamily: 'monospace', letterSpacing: 0.5 }}>
              <span>cmd+shift+d</span>
              <span>
                {summary?.total || 0}
                {pendingCount > 0 && ` · ${pendingCount}p`}
                {runningCount > 0 && ` · ${runningCount}r`}
                {holdCount > 0 && ` · ${holdCount}h`}
              </span>
            </div>

            {/* MARKER_130.C18A: Agent Status Row */}
            {activeAgents.length > 0 && (
              <div style={{
                marginBottom: 10,
                padding: '8px 10px',
                background: 'rgba(255,255,255,0.02)',
                borderRadius: 3,
                border: '1px solid rgba(255,255,255,0.04)',
              }}>
                {activeAgents.map((agent) => {
                  const elapsed = agent.elapsed_seconds || 0;
                  const timeStr = elapsed < 60 ? `${elapsed}s` : `${Math.floor(elapsed / 60)}m`;
                  const isRunning = agent.status === 'running';
                  return (
                    <div
                      key={agent.agent_name}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        padding: '3px 0',
                        fontFamily: 'monospace',
                        fontSize: 10,
                      }}
                    >
                      <span style={{
                        width: 6,
                        height: 6,
                        borderRadius: '50%',
                        background: isRunning ? '#4a4' : '#555',
                        animation: isRunning ? 'pulse 1.5s infinite' : 'none',
                      }} />
                      <span style={{ color: '#888', width: 48 }}>{agent.agent_name}</span>
                      <span style={{ color: '#666', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {agent.task_title?.slice(0, 30) || agent.task_id}
                      </span>
                      <span style={{ color: '#555' }}>{timeStr}</span>
                    </div>
                  );
                })}
              </div>
            )}

            {/* MARKER_128.5B: Quick Add — with preset selector and Add & Run */}
            <div style={{ display: 'flex', gap: 4, marginBottom: 10 }}>
              <input
                type="text"
                placeholder="new task..."
                value={newTaskTitle}
                onChange={(e) => setNewTaskTitle(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddTask(false)}
                style={{
                  flex: 1,
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  borderRadius: 3,
                  color: '#ccc',
                  padding: '7px 10px',
                  fontSize: 11,
                  fontFamily: 'monospace',
                  outline: 'none',
                  transition: 'border-color 0.15s',
                }}
              />
              {/* Team selector */}
              <select
                value={newTaskTeam}
                onChange={(e) => setNewTaskTeam(e.target.value as 'dragon' | 'titan')}
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  borderRadius: 3,
                  color: '#666',
                  fontSize: 10,
                  fontFamily: 'monospace',
                  padding: '4px',
                  outline: 'none',
                }}
              >
                <option value="dragon">DRG</option>
                <option value="titan">TTN</option>
              </select>
              {/* MARKER_128.5C: Preset selector (only for dragon) */}
              {newTaskTeam === 'dragon' && (
                <select
                  value={newTaskPreset}
                  onChange={(e) => setNewTaskPreset(e.target.value)}
                  style={{
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.06)',
                    borderRadius: 3,
                    color: '#555',
                    fontSize: 9,
                    fontFamily: 'monospace',
                    padding: '2px',
                    outline: 'none',
                  }}
                >
                  <option value="dragon_bronze">bronze</option>
                  <option value="dragon_silver">silver</option>
                  <option value="dragon_gold">gold</option>
                </select>
              )}
              {/* Add button (queue only) */}
              <button
                onClick={() => handleAddTask(false)}
                disabled={!newTaskTitle.trim()}
                style={{
                  background: newTaskTitle.trim() ? 'rgba(255,255,255,0.08)' : 'transparent',
                  color: newTaskTitle.trim() ? '#ccc' : '#333',
                  border: `1px solid ${newTaskTitle.trim() ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.04)'}`,
                  borderRadius: 3,
                  padding: '6px 8px',
                  fontSize: 12,
                  fontFamily: 'monospace',
                  cursor: newTaskTitle.trim() ? 'pointer' : 'not-allowed',
                  fontWeight: 600,
                  transition: 'all 0.15s',
                }}
                title="Add to queue"
              >
                +
              </button>
              {/* MARKER_128.5B: Add & Run button */}
              <button
                onClick={() => handleAddTask(true)}
                disabled={!newTaskTitle.trim()}
                style={{
                  background: newTaskTitle.trim() ? '#2d3d5a' : 'transparent',
                  color: newTaskTitle.trim() ? '#8af' : '#333',
                  border: `1px solid ${newTaskTitle.trim() ? '#3d4d6a' : 'rgba(255,255,255,0.04)'}`,
                  borderRadius: 3,
                  padding: '6px 8px',
                  fontSize: 12,
                  fontFamily: 'monospace',
                  cursor: newTaskTitle.trim() ? 'pointer' : 'not-allowed',
                  fontWeight: 600,
                  transition: 'all 0.15s',
                }}
                title="Add & Run immediately"
              >
                ▶
              </button>
            </div>

            {/* MARKER_134.C34J: Status Filter */}
            <div style={{
              display: 'flex',
              gap: 4,
              marginBottom: 8,
              fontSize: 9,
              fontFamily: 'monospace',
            }}>
              {(['all', 'pending', 'running', 'done'] as const).map(f => (
                <button
                  key={f}
                  onClick={() => setStatusFilter(f)}
                  style={{
                    padding: '3px 8px',
                    background: statusFilter === f ? 'rgba(255,255,255,0.08)' : 'transparent',
                    border: `1px solid ${statusFilter === f ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.05)'}`,
                    borderRadius: 2,
                    color: statusFilter === f ? '#ccc' : '#555',
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                >
                  {f}
                </button>
              ))}
            </div>

            {/* Task List */}
            <div style={{ flex: 1, overflowY: 'auto', marginBottom: 10, minHeight: 0 }}>
              {loading && tasks.length === 0 && (
                <div style={{ color: '#555', textAlign: 'center', padding: 20, fontSize: 12 }}>
                  Loading...
                </div>
              )}
              {!loading && tasks.length === 0 && (
                <div style={{ color: '#444', textAlign: 'center', padding: 20, fontSize: 12, lineHeight: 1.5 }}>
                  No tasks yet.<br />
                  Use <code style={{ color: '#888' }}>@doctor</code> or <code style={{ color: '#888' }}>@dragon</code> in chat.
                </div>
              )}
              {tasks
                .filter(t => statusFilter === 'all' || t.status === statusFilter || (statusFilter === 'done' && t.status === 'failed'))
                .map((task, idx) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  isSelected={tasks.indexOf(task) === selectedTaskIdx}
                  onPriorityChange={handlePriorityChange}
                  onRemove={handleRemove}
                  onDispatch={handleDispatchTask}
                  onCancel={handleCancelTask}
                />
              ))}
            </div>

            {/* Footer — serious dispatch bar */}
            <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
              <button
                onClick={handleDispatchNext}
                disabled={pendingCount === 0}
                style={{
                  width: '100%',
                  padding: '10px 16px',
                  background: pendingCount > 0
                    ? 'rgba(255,255,255,0.06)'
                    : 'rgba(255,255,255,0.02)',
                  color: pendingCount > 0 ? '#e0e0e0' : '#333',
                  border: `1px solid ${pendingCount > 0 ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.04)'}`,
                  borderRadius: 3,
                  fontSize: 10,
                  fontFamily: 'monospace',
                  fontWeight: 600,
                  cursor: pendingCount > 0 ? 'pointer' : 'not-allowed',
                  letterSpacing: 2,
                  textTransform: 'uppercase',
                  transition: 'all 0.2s',
                  backdropFilter: pendingCount > 0 ? 'blur(4px)' : 'none',
                }}
              >
                dispatch next {pendingCount > 0 && `(${pendingCount})`}
              </button>

              {/* MARKER_131.C22: Heartbeat controls — unified style */}
              <div
                onClick={() => setHeartbeatExpanded(!heartbeatExpanded)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 10px',
                  background: 'rgba(255,255,255,0.03)',
                  borderRadius: 3,
                  cursor: 'pointer',
                  fontSize: 11,
                  fontFamily: 'monospace',
                }}
              >
                <span style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: heartbeat?.enabled ? '#6a6' : '#444',
                  boxShadow: heartbeat?.enabled ? '0 0 6px rgba(100,160,100,0.4)' : 'none',
                }} />
                <span style={{ color: '#aaa', fontWeight: 500 }}>Heartbeat</span>
                <span style={{
                  color: heartbeat?.enabled ? '#8a8' : '#666',
                  padding: '2px 6px',
                  background: heartbeat?.enabled ? 'rgba(100,160,100,0.1)' : 'rgba(255,255,255,0.03)',
                  borderRadius: 2,
                  fontSize: 10,
                }}>
                  {heartbeat?.enabled ? 'ON' : 'OFF'}
                </span>
                <span style={{ flex: 1 }} />
                {/* MARKER_136.W1B: Show countdown when enabled */}
                {heartbeat?.enabled && nextTickIn !== null ? (
                  <span style={{ color: nextTickIn <= 10 ? '#8a8' : '#666' }}>
                    next in {formatInterval(nextTickIn)}
                  </span>
                ) : (
                  <span style={{ color: '#666' }}>
                    {heartbeat ? formatInterval(heartbeat.interval) : '-'}
                  </span>
                )}
                <span style={{ color: '#555' }}>{heartbeatExpanded ? '▾' : '▸'}</span>
              </div>

              {heartbeatExpanded && heartbeat && (
                <div style={{
                  padding: '10px 12px',
                  background: 'rgba(255,255,255,0.02)',
                  borderRadius: 3,
                  fontSize: 11,
                  fontFamily: 'monospace',
                }}>
                  {/* MARKER_133.C33G: Controls right-aligned */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
                    <span style={{ color: '#888' }}>Heartbeat Controls</span>
                    <span style={{ flex: 1 }} />
                    <span style={{ color: '#666' }}>interval:</span>
                    <select
                      value={heartbeat.interval}
                      onChange={(e) => { e.stopPropagation(); updateHeartbeat({ interval: parseInt(e.target.value) }); }}
                      onClick={(e) => e.stopPropagation()}
                      style={{
                        background: '#1a1a1a',
                        border: '1px solid #333',
                        borderRadius: 3,
                        color: '#ccc',
                        fontSize: 11,
                        padding: '4px 8px',
                      }}
                    >
                      <option value="30">30 sec</option>
                      <option value="60">1 min</option>
                      <option value="120">2 min</option>
                      <option value="300">5 min</option>
                      <option value="900">15 min</option>
                      <option value="1800">30 min</option>
                      <option value="3600">1 hour</option>
                      <option value="21600">6 hours</option>
                      <option value="43200">12 hours</option>
                      <option value="86400">1 day</option>
                      <option value="604800">1 week</option>
                    </select>
                    {/* ON/OFF toggle buttons — now on right */}
                    <div style={{ display: 'flex', gap: 0 }}>
                      <button
                        onClick={(e) => { e.stopPropagation(); updateHeartbeat({ enabled: true }); }}
                        style={{
                          padding: '4px 12px',
                          background: heartbeat.enabled ? '#2a3a2a' : 'transparent',
                          border: `1px solid ${heartbeat.enabled ? '#3a4a3a' : '#333'}`,
                          borderRadius: '3px 0 0 3px',
                          color: heartbeat.enabled ? '#8a8' : '#555',
                          fontSize: 10,
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        ON
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); updateHeartbeat({ enabled: false }); }}
                        style={{
                          padding: '4px 12px',
                          background: !heartbeat.enabled ? '#3a2a2a' : 'transparent',
                          border: `1px solid ${!heartbeat.enabled ? '#4a3a3a' : '#333'}`,
                          borderRadius: '0 3px 3px 0',
                          color: !heartbeat.enabled ? '#a88' : '#555',
                          fontSize: 10,
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        OFF
                      </button>
                    </div>
                  </div>
                  {/* MARKER_136.W1B: Stats row (countdown removed - shown in header) */}
                  <div style={{ display: 'flex', gap: 16, color: '#777', fontSize: 10 }}>
                    <span>ticks: <span style={{ color: '#aaa' }}>{heartbeat.total_ticks}</span></span>
                    <span>dispatched: <span style={{ color: '#aaa' }}>{heartbeat.tasks_dispatched}</span></span>
                    {heartbeat.last_tick > 0 && (
                      <span>last: <span style={{ color: '#aaa' }}>{new Date(heartbeat.last_tick * 1000).toLocaleTimeString()}</span></span>
                    )}
                  </div>
                </div>
              )}

              {/* Save positions — unified style */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '8px 10px',
                background: 'rgba(255,255,255,0.02)',
                borderRadius: 3,
                fontSize: 11,
                fontFamily: 'monospace',
              }}>
                <span style={{ color: '#888' }}>Save Positions</span>
                <div style={{ display: 'flex', gap: 4 }}>
                  <button
                    onClick={() => useStore.getState().setPersistPositions(true)}
                    style={{
                      padding: '4px 10px',
                      background: useStore.getState().persistPositions ? '#2a3a2a' : 'transparent',
                      border: `1px solid ${useStore.getState().persistPositions ? '#3a4a3a' : '#333'}`,
                      borderRadius: '3px 0 0 3px',
                      color: useStore.getState().persistPositions ? '#8a8' : '#555',
                      fontSize: 10,
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    ON
                  </button>
                  <button
                    onClick={() => useStore.getState().setPersistPositions(false)}
                    style={{
                      padding: '4px 10px',
                      background: !useStore.getState().persistPositions ? '#3a2a2a' : 'transparent',
                      border: `1px solid ${!useStore.getState().persistPositions ? '#4a3a3a' : '#333'}`,
                      borderRadius: '0 3px 3px 0',
                      color: !useStore.getState().persistPositions ? '#a88' : '#555',
                      fontSize: 10,
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    OFF
                  </button>
                </div>
                <span style={{ flex: 1 }} />
                <button
                  onClick={() => useStore.getState().resetLayout()}
                  style={{
                    padding: '4px 12px',
                    background: 'transparent',
                    border: '1px solid #333',
                    borderRadius: 3,
                    color: '#666',
                    cursor: 'pointer',
                    fontSize: 10,
                    fontFamily: 'monospace',
                    transition: 'all 0.15s',
                  }}
                >
                  Reset Layout
                </button>
              </div>
            </div>
          </>
        )}

        {/* ═══ STATS TAB ═══ */}
        {activeTab === 'stats' && <PipelineStats tasks={tasks} />}

        {/* ═══ ARCHITECT TAB ═══ MARKER_136.W2B */}
        {activeTab === 'architect' && <ArchitectChat />}

        {/* ═══ BALANCE TAB ═══ MARKER_126.7 */}
        {activeTab === 'balance' && <BalancesPanel />}

        {/* MARKER_136.W1A: ACTIVITY tab removed (Wave 1 cleanup) */}

        {/* ═══ WATCHER TAB ═══ MARKER_129.1B */}
        {activeTab === 'watcher' && <WatcherStats />}

        {/* ═══ ARTIFACTS TAB ═══ MARKER_C23C */}
        {activeTab === 'artifacts' && <ArtifactViewer />}
      </div>

      {/* MARKER_C23D: Multi-Agent Status Bar */}
      <AgentStatusBar />

      {/* MARKER_128.7A: Toast notifications */}
      {toasts.length > 0 && (
        <div style={{
          position: 'fixed',
          bottom: 20,
          right: 20,
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
          zIndex: 10000,
        }}>
          {toasts.map(toast => (
            <div
              key={toast.id}
              onClick={() => {
                // Click to switch to Board tab and expand task
                if (toast.taskId) {
                  setActiveTab('board');
                  const idx = tasks.findIndex(t => t.id === toast.taskId);
                  if (idx >= 0) setSelectedTaskIdx(idx);
                  window.dispatchEvent(new CustomEvent('task-expand', { detail: { taskId: toast.taskId } }));
                }
                setToasts(prev => prev.filter(t => t.id !== toast.id));
              }}
              style={{
                background: '#1a1a1a',
                borderLeft: `3px solid ${toast.type === 'success' ? '#2d5a3d' : '#5a2d2d'}`,
                padding: '10px 14px',
                borderRadius: 3,
                color: '#ccc',
                fontSize: 11,
                fontFamily: 'monospace',
                cursor: 'pointer',
                boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
                animation: 'slideUp 0.2s ease-out',
                maxWidth: 300,
              }}
            >
              {toast.message}
            </div>
          ))}
        </div>
      )}

      {/* MARKER_128.7A: Toast animation keyframes + MARKER_130.C18A: Agent pulse */}
      <style>{`
        @keyframes slideUp {
          from { transform: translateY(20px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </>
  );

  // MARKER_134.C34E: Standalone mode - direct render without window chrome
  if (standalone) {
    return (
      <div style={{
        width: '100%',
        height: '100%',
        background: '#0d0d0d',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}>
        {content}
      </div>
    );
  }

  // Normal floating window mode
  return (
    <FloatingWindow
      title="Dev Panel"
      isOpen={isOpen}
      onClose={onClose}
      defaultWidth={420}
      defaultHeight={600}
    >
      {content}
    </FloatingWindow>
  );
}
