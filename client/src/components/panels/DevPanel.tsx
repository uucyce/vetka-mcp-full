/**
 * MARKER_124.2C: DevPanel → Task Board UI
 * Phase 124.2C: Replaced Y-axis sliders and fallback settings with
 * Task Board management panel. Keeps spatial memory controls.
 *
 * Features:
 * - Task list from backend (GET /api/debug/task-board)
 * - Priority badges, status chips, phase type icons
 * - Quick-add task input
 * - Dispatch next button
 * - Spatial Memory controls (persist positions, reset cache)
 *
 * @status active
 * @phase 124.2
 * @depends react, FloatingWindow, TaskCard, useStore
 * @used_by App
 */

import { useState, useEffect, useCallback } from 'react';
import { FloatingWindow } from '../artifact/FloatingWindow';
import { useStore } from '../../store/useStore';
import { TaskCard, TaskData } from './TaskCard';

interface DevPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const API_BASE = 'http://localhost:5001/api/debug';

// MARKER_124.2C: Task Board panel component
export function DevPanel({ isOpen, onClose }: DevPanelProps) {
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

  // Fetch on open and poll every 10s
  useEffect(() => {
    if (!isOpen) return;
    fetchTasks();
    const interval = setInterval(fetchTasks, 10000);
    return () => clearInterval(interval);
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

  return (
    <FloatingWindow
      title="Task Board"
      isOpen={isOpen}
      onClose={onClose}
      defaultWidth={380}
      defaultHeight={560}
    >
      {/* Header with shortcut hint and summary */}
      <div style={{ padding: '4px 12px 0', color: '#666', fontSize: 11, display: 'flex', justifyContent: 'space-between' }}>
        <span>Cmd+Shift+D to toggle</span>
        {summary && (
          <span>
            {summary.total} tasks
            {pendingCount > 0 && ` · ${pendingCount} pending`}
            {runningCount > 0 && ` · ${runningCount} running`}
          </span>
        )}
      </div>

      <div style={{
        padding: 12,
        paddingTop: 8,
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100% - 24px)',
        color: '#e0e0e0',
        fontSize: 13,
      }}>
        {/* Quick Add Section */}
        <div style={{
          display: 'flex',
          gap: 6,
          marginBottom: 10,
        }}>
          <input
            type="text"
            placeholder="New task..."
            value={newTaskTitle}
            onChange={(e) => setNewTaskTitle(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddTask()}
            style={{
              flex: 1,
              background: '#1e1e1e',
              border: '1px solid #333',
              borderRadius: 4,
              color: '#e0e0e0',
              padding: '6px 10px',
              fontSize: 12,
              outline: 'none',
            }}
          />
          <select
            value={newTaskTeam}
            onChange={(e) => setNewTaskTeam(e.target.value as 'dragon' | 'titan')}
            style={{
              background: '#1e1e1e',
              border: '1px solid #333',
              borderRadius: 4,
              color: '#ccc',
              fontSize: 11,
              padding: '4px',
            }}
          >
            <option value="dragon">🐉</option>
            <option value="titan">⚡</option>
          </select>
          <button
            onClick={handleAddTask}
            disabled={!newTaskTitle.trim()}
            style={{
              background: newTaskTitle.trim() ? '#2563eb' : '#333',
              color: newTaskTitle.trim() ? '#fff' : '#666',
              border: 'none',
              borderRadius: 4,
              padding: '6px 12px',
              fontSize: 13,
              cursor: newTaskTitle.trim() ? 'pointer' : 'not-allowed',
              fontWeight: 600,
            }}
          >
            +
          </button>
        </div>

        {/* Task List */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          marginBottom: 10,
          minHeight: 0,
        }}>
          {loading && tasks.length === 0 && (
            <div style={{ color: '#666', textAlign: 'center', padding: 20, fontSize: 12 }}>
              Loading...
            </div>
          )}

          {!loading && tasks.length === 0 && (
            <div style={{ color: '#555', textAlign: 'center', padding: 20, fontSize: 12, lineHeight: 1.5 }}>
              No tasks yet.<br />
              Use <code style={{ color: '#888' }}>@doctor</code> or <code style={{ color: '#888' }}>@dragon</code> in chat,<br />
              or add one above.
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

        {/* Footer: Dispatch + Spatial Memory */}
        <div style={{
          borderTop: '1px solid #333',
          paddingTop: 10,
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
        }}>
          {/* Dispatch button */}
          <button
            onClick={handleDispatchNext}
            disabled={pendingCount === 0}
            style={{
              width: '100%',
              padding: '8px 16px',
              background: pendingCount > 0 ? '#2563eb' : '#333',
              color: pendingCount > 0 ? '#fff' : '#666',
              border: 'none',
              borderRadius: 4,
              fontSize: 13,
              fontWeight: 500,
              cursor: pendingCount > 0 ? 'pointer' : 'not-allowed',
            }}
          >
            ▶ Dispatch Next {pendingCount > 0 && `(${pendingCount} pending)`}
          </button>

          {/* Spatial Memory — kept from Phase 113.4 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', flex: 1 }}>
              <input
                type="checkbox"
                checked={useStore.getState().persistPositions}
                onChange={(e) => useStore.getState().setPersistPositions(e.target.checked)}
                style={{ accentColor: '#a855f7' }}
              />
              <span style={{ color: '#888' }}>Persist Positions</span>
            </label>
            <button
              onClick={() => {
                useStore.getState().resetLayout();
                alert('Position cache cleared. Reload page for API defaults.');
              }}
              style={{
                padding: '3px 8px',
                background: '#331111',
                border: '1px solid #662222',
                borderRadius: 3,
                color: '#ff6666',
                cursor: 'pointer',
                fontSize: 10,
              }}
            >
              Reset Positions
            </button>
          </div>
        </div>
      </div>
    </FloatingWindow>
  );
}
