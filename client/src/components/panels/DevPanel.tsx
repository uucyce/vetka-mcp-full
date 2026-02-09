/**
 * MARKER_126.0C: DevPanel — Task Board + Stats + League Tester
 * MARKER_126.2B: Style upgrade — Nolan glassmorphism, monospace, no emoji
 * Phase 126.2: "Batman Nolan, not Burton" — dark, serious, minimal.
 *
 * @status active
 * @phase 126.2
 * @depends FloatingWindow, TaskCard, PipelineStats, LeagueTester, useStore
 */

import { useState, useEffect, useCallback } from 'react';
import { FloatingWindow } from '../artifact/FloatingWindow';
import { useStore } from '../../store/useStore';
import { TaskCard, TaskData } from './TaskCard';
import { PipelineStats } from './PipelineStats';
import { LeagueTester } from './LeagueTester';

interface DevPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const API_BASE = 'http://localhost:5001/api/debug';

type Tab = 'board' | 'stats' | 'test';

const TABS: { id: Tab; label: string }[] = [
  { id: 'board', label: 'Board' },
  { id: 'stats', label: 'Stats' },
  { id: 'test', label: 'Test' },
];

// MARKER_126.0C: Tabbed DevPanel
export function DevPanel({ isOpen, onClose }: DevPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>('board');
  const [tasks, setTasks] = useState<TaskData[]>([]);
  const [loading, setLoading] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskTeam, setNewTaskTeam] = useState<'dragon' | 'titan'>('dragon');
  const [summary, setSummary] = useState<{ total: number; by_status: Record<string, number> } | null>(null);

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
    } catch (err) {
      console.error('[TaskBoard] Fetch failed:', err);
    } finally {
      setLoading(false);
    }
  }, [isOpen]);

  // Fetch on open, poll every 30s, and listen for SocketIO updates
  // MARKER_124.3D: Live updates via task-board-updated CustomEvent
  useEffect(() => {
    if (!isOpen) return;
    fetchTasks();
    const interval = setInterval(fetchTasks, 30000);

    const handleBoardUpdate = () => { fetchTasks(); };
    window.addEventListener('task-board-updated', handleBoardUpdate);

    return () => {
      clearInterval(interval);
      window.removeEventListener('task-board-updated', handleBoardUpdate);
    };
  }, [isOpen, fetchTasks]);

  // Add task
  const handleAddTask = useCallback(async () => {
    if (!newTaskTitle.trim()) return;

    try {
      const res = await fetch(`${API_BASE}/task-board/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newTaskTitle.trim(),
          phase_type: newTaskTeam === 'titan' ? 'research' : 'build',
          preset: newTaskTeam === 'titan' ? 'titan_core' : 'dragon_silver',
          tags: [newTaskTeam],
        }),
      });
      if (res.ok) {
        setNewTaskTitle('');
        fetchTasks();
      }
    } catch (err) {
      console.error('[TaskBoard] Add failed:', err);
    }
  }, [newTaskTitle, newTaskTeam, fetchTasks]);

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

  // Dispatch specific task
  const handleDispatchTask = useCallback(async (taskId: string) => {
    try {
      await fetch(`${API_BASE}/task-board/dispatch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: taskId }),
      });
      fetchTasks();
    } catch (err) {
      console.error('[TaskBoard] Dispatch failed:', err);
    }
  }, [fetchTasks]);

  // Dispatch next (highest priority)
  const handleDispatchNext = useCallback(async () => {
    try {
      await fetch(`${API_BASE}/task-board/dispatch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      fetchTasks();
    } catch (err) {
      console.error('[TaskBoard] Dispatch next failed:', err);
    }
  }, [fetchTasks]);

  if (!isOpen) return null;

  const pendingCount = tasks.filter(t => t.status === 'pending').length;
  const runningCount = tasks.filter(t => t.status === 'running').length;
  const holdCount = tasks.filter(t => t.status === 'hold').length;

  return (
    <FloatingWindow
      title="Dev Panel"
      isOpen={isOpen}
      onClose={onClose}
      defaultWidth={420}
      defaultHeight={600}
    >
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
      </div>

      <div style={{
        padding: 12,
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100% - 36px)',
        color: '#e0e0e0',
        fontSize: 13,
      }}>
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

            {/* Quick Add — monospace, dark glass */}
            <div style={{ display: 'flex', gap: 4, marginBottom: 10 }}>
              <input
                type="text"
                placeholder="new task..."
                value={newTaskTitle}
                onChange={(e) => setNewTaskTitle(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddTask()}
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
              <button
                onClick={handleAddTask}
                disabled={!newTaskTitle.trim()}
                style={{
                  background: newTaskTitle.trim() ? 'rgba(255,255,255,0.08)' : 'transparent',
                  color: newTaskTitle.trim() ? '#ccc' : '#333',
                  border: `1px solid ${newTaskTitle.trim() ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.04)'}`,
                  borderRadius: 3,
                  padding: '6px 12px',
                  fontSize: 12,
                  fontFamily: 'monospace',
                  cursor: newTaskTitle.trim() ? 'pointer' : 'not-allowed',
                  fontWeight: 600,
                  transition: 'all 0.15s',
                }}
              >
                +
              </button>
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
              {tasks.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  onPriorityChange={handlePriorityChange}
                  onRemove={handleRemove}
                  onDispatch={handleDispatchTask}
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

              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 9 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', flex: 1 }}>
                  <input
                    type="checkbox"
                    checked={useStore.getState().persistPositions}
                    onChange={(e) => useStore.getState().setPersistPositions(e.target.checked)}
                    style={{ accentColor: '#555' }}
                  />
                  <span style={{ color: '#444', fontFamily: 'monospace' }}>persist positions</span>
                </label>
                <button
                  onClick={() => {
                    useStore.getState().resetLayout();
                  }}
                  style={{
                    padding: '3px 8px',
                    background: 'transparent',
                    border: '1px solid rgba(255,255,255,0.06)',
                    borderRadius: 2,
                    color: '#555',
                    cursor: 'pointer',
                    fontSize: 9,
                    fontFamily: 'monospace',
                    transition: 'all 0.15s',
                  }}
                >
                  reset
                </button>
              </div>
            </div>
          </>
        )}

        {/* ═══ STATS TAB ═══ */}
        {activeTab === 'stats' && <PipelineStats tasks={tasks} />}

        {/* ═══ TEST TAB ═══ */}
        {activeTab === 'test' && <LeagueTester onTestComplete={fetchTasks} />}
      </div>
    </FloatingWindow>
  );
}
