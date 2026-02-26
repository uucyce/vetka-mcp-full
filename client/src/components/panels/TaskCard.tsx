/**
 * MARKER_126.2A: TaskCard — Nolan dark style, no emoji.
 * MARKER_127.0B: Results Viewer — expand to see pipeline results/code
 * MARKER_128.2C: Apply button — write code to disk
 * MARKER_128.3B/C: Result lifecycle badges + action buttons
 * MARKER_130.C18B: Commit column — agent badge + commit hash
 * CSS-only status indicators, monochrome priority, glassmorphism accents.
 * Phase 130: Agent coordination — who committed what.
 *
 * @status active
 * @phase 130
 * @depends react
 * @used_by DevPanel
 */

import { useState, useCallback, useEffect, memo } from 'react';
import { DiffViewer } from './DiffViewer';  // MARKER_128.4B

export interface PipelineStatsData {
  preset?: string;
  league?: string;
  phase_type?: string;
  subtasks_total?: number;
  subtasks_completed?: number;
  success?: boolean;
  llm_calls?: number;
  tokens_in?: number;
  tokens_out?: number;
  verifier_avg_confidence?: number;
  duration_s?: number;
  completed_at?: number;
}

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
  stats?: PipelineStatsData;
  pipeline_task_id?: string;  // MARKER_127.0B: Link to pipeline_tasks.json
  // MARKER_128.3: Result lifecycle fields
  result_status?: 'applied' | 'rejected' | 'rework' | null;
  result_reviewed_at?: string;
  result_review_reason?: string;
  // MARKER_130.C18B: Agent coordination fields
  assigned_to?: string;
  agent_type?: string;
  commit_hash?: string;
  commit_message?: string;
  completed_at?: string;
  // MARKER_155.1A: Task dependencies for DAG edges at tasks level
  dependencies?: string[];
  // MARKER_155.2A: Roadmap module assignment for drill-down filtering
  module?: string;
  // MARKER_155A.P1.CROSSCUT_TASKS: Unified graph contract for cross-cutting tasks
  primary_node_id?: string;
  affected_nodes?: string[];
  integration_task_of?: string[];
  // MARKER_155.G1.TASK_ANCHORING_CONTRACT_V1: execution metadata
  workflow_id?: string;
  team_profile?: string;
  task_origin?: 'architect' | 'chat' | 'manual' | 'system' | string;
}

// MARKER_127.0B: Pipeline results data structure
// MARKER_C23A: Added verifier_feedback for RALF loop display
interface VerifierFeedback {
  passed: boolean;
  confidence: number;
  retry_count?: number;
  max_retries?: number;
  escalated?: boolean;
  feedback?: string;
}

interface SubtaskResult {
  description: string;
  status: string;
  result?: string;
  marker?: string;
  needs_research?: boolean;
  diff_patch?: string;  // MARKER_128.4B: Unified diff from backend
  original_file?: string;  // MARKER_128.4B: Original file path
  // MARKER_C23A: RALF loop verifier feedback
  verifier_feedback?: VerifierFeedback;
}

interface PipelineResults {
  success: boolean;
  task_id: string;
  pipeline_task_id?: string;
  status?: string;
  phase_type?: string;
  subtasks: SubtaskResult[];
  results_summary?: Record<string, unknown>;
  message?: string;
}

interface TaskCardProps {
  task: TaskData;
  isSelected?: boolean;  // MARKER_128.9A: Keyboard navigation highlight
  onPriorityChange?: (taskId: string, priority: number) => void;
  onRemove?: (taskId: string) => void;
  onDispatch?: (taskId: string, preset?: string) => void;  // MARKER_128.5A: Added preset param
  onCancel?: (taskId: string) => void;  // MARKER_126.5G: Stop button
}

// Priority: monochrome gradient, P1=brightest, P5=dimmest
const PRIORITY_STYLE: Record<number, { bg: string; border: string; text: string }> = {
  1: { bg: '#e0e0e0', border: '#fff', text: '#000' },
  2: { bg: '#aaa', border: '#ccc', text: '#111' },
  3: { bg: '#666', border: '#888', text: '#eee' },
  4: { bg: '#444', border: '#666', text: '#ccc' },
  5: { bg: '#2a2a2a', border: '#444', text: '#888' },
};

// Status: CSS indicators instead of emoji
// dot = small circle, pulse = animated ring, bar = horizontal line
type StatusShape = 'dot' | 'pulse' | 'ring' | 'bar' | 'x';

interface StatusDef {
  shape: StatusShape;
  color: string;
  glow?: string;
  label: string;
}

const STATUS_DEF: Record<string, StatusDef> = {
  pending:   { shape: 'dot',   color: '#555',    label: 'pending' },
  queued:    { shape: 'dot',   color: '#888',    label: 'queued' },
  running:   { shape: 'pulse', color: '#e0e0e0', glow: 'rgba(224,224,224,0.3)', label: 'running' },
  done:      { shape: 'ring',  color: '#8a8',    label: 'done' },
  failed:    { shape: 'x',     color: '#a66',    label: 'failed' },
  cancelled: { shape: 'bar',   color: '#555',    label: 'cancelled' },
  hold:      { shape: 'bar',   color: '#a98',    label: 'hold' },
};

// Phase type: minimal monochrome symbols (no emoji)
const PHASE_SYMBOL: Record<string, string> = {
  build: '▸',
  fix: '×',
  research: '◎',
};

// MARKER_128.3B: Result lifecycle status colors (Nolan muted)
const RESULT_STATUS_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  applied: { bg: '#2d5a2d', color: '#8a8', label: '✓ applied' },
  rejected: { bg: '#5a2d2d', color: '#a88', label: '✕ rejected' },
  rework: { bg: '#5a4a2d', color: '#aa8', label: '↺ rework' },
};

// ── CSS Status Indicator ──
function StatusIndicator({ status }: { status: string }) {
  const def = STATUS_DEF[status] || STATUS_DEF.pending;
  const size = 8;

  if (def.shape === 'pulse') {
    return (
      <span style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: size + 8, height: size + 8 }}>
        {/* Pulsing outer ring */}
        <span style={{
          position: 'absolute',
          width: size + 6,
          height: size + 6,
          borderRadius: '50%',
          border: `1px solid ${def.color}`,
          opacity: 0.4,
          animation: 'taskPulse 1.5s ease-in-out infinite',
        }} />
        {/* Solid inner dot */}
        <span style={{
          width: size,
          height: size,
          borderRadius: '50%',
          background: def.color,
          boxShadow: def.glow ? `0 0 6px ${def.glow}` : 'none',
        }} />
      </span>
    );
  }

  if (def.shape === 'ring') {
    return (
      <span style={{
        display: 'inline-block',
        width: size,
        height: size,
        borderRadius: '50%',
        border: `2px solid ${def.color}`,
        background: 'transparent',
      }} />
    );
  }

  if (def.shape === 'x') {
    return (
      <span style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: size + 2,
        height: size + 2,
        color: def.color,
        fontSize: 10,
        fontWeight: 700,
        fontFamily: 'monospace',
        lineHeight: 1,
      }}>✕</span>
    );
  }

  if (def.shape === 'bar') {
    return (
      <span style={{
        display: 'inline-block',
        width: 10,
        height: 2,
        background: def.color,
        borderRadius: 1,
        marginTop: 1,
      }} />
    );
  }

  // Default: dot
  return (
    <span style={{
      display: 'inline-block',
      width: size,
      height: size,
      borderRadius: '50%',
      background: def.color,
    }} />
  );
}

// ── Inject keyframe animation (once) ──
let _injected = false;
function injectKeyframes() {
  if (_injected || typeof document === 'undefined') return;
  const style = document.createElement('style');
  style.textContent = `
    @keyframes taskPulse {
      0%, 100% { transform: scale(1); opacity: 0.4; }
      50% { transform: scale(1.4); opacity: 0.1; }
    }
  `;
  document.head.appendChild(style);
  _injected = true;
}

const API_BASE = 'http://localhost:5001/api/debug';

// ── TaskCard ──
// MARKER_129.3A: Wrap with React.memo to prevent unnecessary re-renders
export const TaskCard = memo(function TaskCard({ task, isSelected, onPriorityChange, onRemove, onDispatch, onCancel }: TaskCardProps) {
  injectKeyframes();
  const [expanded, setExpanded] = useState(false);
  const [hover, setHover] = useState(false);

  // MARKER_127.0B: Results viewing state
  const [showResults, setShowResults] = useState(false);
  const [results, setResults] = useState<PipelineResults | null>(null);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [resultsError, setResultsError] = useState<string | null>(null);
  const [expandedSubtask, setExpandedSubtask] = useState<number | null>(null);

  // MARKER_128.2C: Apply state
  const [applyingSubtask, setApplyingSubtask] = useState<number | null>(null);
  const [applyResult, setApplyResult] = useState<{ idx: number; success: boolean; message: string } | null>(null);

  // MARKER_128.8A: Apply All state
  const [applyingAll, setApplyingAll] = useState(false);
  const [applyAllProgress, setApplyAllProgress] = useState<{ current: number; total: number } | null>(null);

  // MARKER_128.3B: Local result status (synced from props)
  const [localResultStatus, setLocalResultStatus] = useState(task.result_status);

  // MARKER_128.5C: Preset selector state (default from task or silver)
  const [selectedPreset, setSelectedPreset] = useState(task.preset || 'dragon_silver');

  // MARKER_128.4B: View mode for subtask results (code vs diff)
  const [subtaskViewMode, setSubtaskViewMode] = useState<Record<number, 'code' | 'diff'>>({});

  // MARKER_128.9A: Keyboard event handlers
  useEffect(() => {
    const handleExpand = (e: CustomEvent) => {
      if (e.detail?.taskId === task.id) {
        setExpanded(true);
        if (!showResults && (task.status === 'done' || task.status === 'failed')) {
          // Also load results
          fetchResultsInternal();
        }
      }
    };
    const handleApplyAll = (e: CustomEvent) => {
      if (e.detail?.taskId === task.id && results) {
        applyAllResults();
      }
    };
    window.addEventListener('task-expand', handleExpand as EventListener);
    window.addEventListener('task-apply-all', handleApplyAll as EventListener);
    return () => {
      window.removeEventListener('task-expand', handleExpand as EventListener);
      window.removeEventListener('task-apply-all', handleApplyAll as EventListener);
    };
  }, [task.id, task.status, showResults, results]);

  // Internal fetch results (for keyboard trigger)
  const fetchResultsInternal = useCallback(async () => {
    if (results) {
      setShowResults(true);
      return;
    }
    setResultsLoading(true);
    setResultsError(null);
    try {
      const res = await fetch(`${API_BASE}/pipeline-results/${task.id}`);
      const data = await res.json();
      if (data.success) {
        setResults(data);
        setShowResults(true);
      } else {
        setResultsError(data.error || data.message || 'Failed to load results');
      }
    } catch (err) {
      setResultsError(err instanceof Error ? err.message : 'Network error');
    } finally {
      setResultsLoading(false);
    }
  }, [task.id, results]);

  const fetchResults = useCallback(async () => {
    if (results) {
      setShowResults(!showResults);
      return;
    }
    setResultsLoading(true);
    setResultsError(null);
    try {
      const res = await fetch(`${API_BASE}/pipeline-results/${task.id}`);
      const data = await res.json();
      if (data.success) {
        setResults(data);
        setShowResults(true);
      } else {
        setResultsError(data.error || data.message || 'Failed to load results');
      }
    } catch (err) {
      setResultsError(err instanceof Error ? err.message : 'Network error');
    } finally {
      setResultsLoading(false);
    }
  }, [task.id, results, showResults]);

  // MARKER_128.2C: Apply subtask code to disk
  const applySubtask = useCallback(async (subtaskIdx: number) => {
    setApplyingSubtask(subtaskIdx);
    setApplyResult(null);
    try {
      const res = await fetch(`${API_BASE}/pipeline-results/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: task.id, subtask_idx: subtaskIdx }),
      });
      const data = await res.json();
      if (data.success) {
        setApplyResult({ idx: subtaskIdx, success: true, message: `Applied: ${data.files_written.join(', ')}` });
      } else {
        setApplyResult({ idx: subtaskIdx, success: false, message: data.error || 'Apply failed' });
      }
    } catch (err) {
      setApplyResult({ idx: subtaskIdx, success: false, message: err instanceof Error ? err.message : 'Network error' });
    } finally {
      setApplyingSubtask(null);
    }
  }, [task.id]);

  // MARKER_128.3C: Update result status (applied/rejected/rework)
  const updateResultStatus = useCallback(async (status: 'applied' | 'rejected' | 'rework', reason?: string) => {
    try {
      const res = await fetch(`${API_BASE}/pipeline-results/${task.id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status, reason }),
      });
      const data = await res.json();
      if (data.success) {
        setLocalResultStatus(status);
      }
    } catch (err) {
      console.error('Failed to update result status:', err);
    }
  }, [task.id]);

  // MARKER_128.8B: Apply All — sequential apply with progress
  const applyAllResults = useCallback(async () => {
    if (!results?.subtasks || applyingAll) return;

    const subtasksWithCode = results.subtasks
      .map((st, idx) => ({ st, idx }))
      .filter(({ st }) => st.result && st.status === 'done');

    if (subtasksWithCode.length === 0) return;

    setApplyingAll(true);
    setApplyAllProgress({ current: 0, total: subtasksWithCode.length });

    let successCount = 0;
    for (let i = 0; i < subtasksWithCode.length; i++) {
      const { idx } = subtasksWithCode[i];
      setApplyAllProgress({ current: i + 1, total: subtasksWithCode.length });
      try {
        const res = await fetch(`${API_BASE}/pipeline-results/apply`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ task_id: task.id, subtask_idx: idx }),
        });
        const data = await res.json();
        if (data.success) successCount++;
      } catch {
        // Continue even if one fails
      }
    }

    setApplyingAll(false);
    setApplyAllProgress(null);

    // Mark as applied if all succeeded
    if (successCount === subtasksWithCode.length) {
      updateResultStatus('applied');
    }
  }, [results, task.id, applyingAll, updateResultStatus]);

  const hasPipelineResults = task.status === 'done' || task.status === 'failed';

  const prio = PRIORITY_STYLE[task.priority] || PRIORITY_STYLE[5];
  const phaseSymbol = PHASE_SYMBOL[task.phase_type] || '·';
  const isDispatchable = task.status === 'pending' || task.status === 'queued';

  return (
    <div
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        padding: '8px 10px',
        marginBottom: 4,
        background: isSelected
          ? 'rgba(255,255,255,0.06)'
          : hover
            ? 'rgba(255,255,255,0.04)'
            : expanded
              ? 'rgba(255,255,255,0.03)'
              : 'rgba(255,255,255,0.015)',
        borderRadius: 4,
        borderLeft: `2px solid ${isSelected ? '#888' : prio.bg}`,
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        backdropFilter: hover || isSelected ? 'blur(2px)' : 'none',
        outline: isSelected ? '1px solid rgba(255,255,255,0.1)' : 'none',
      }}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Top row: priority + phase + title + status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {/* Priority badge — monochrome */}
        <span
          style={{
            background: prio.bg,
            color: prio.text,
            fontSize: 9,
            fontWeight: 700,
            fontFamily: 'monospace',
            padding: '1px 4px',
            borderRadius: 2,
            minWidth: 18,
            textAlign: 'center',
            letterSpacing: 0.5,
          }}
        >
          P{task.priority}
        </span>

        {/* Phase symbol — no emoji */}
        <span style={{
          fontSize: 11,
          color: '#666',
          fontFamily: 'monospace',
          width: 12,
          textAlign: 'center',
        }}>{phaseSymbol}</span>

        {/* Title */}
        <span
          style={{
            flex: 1,
            fontSize: 12,
            color: '#ccc',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            fontWeight: 400,
          }}
        >
          {task.title}
        </span>

        {/* MARKER_130.C18B: Agent badge */}
        {task.assigned_to && (
          <span style={{
            fontSize: 9,
            color: '#666',
            background: 'rgba(255,255,255,0.04)',
            padding: '1px 5px',
            borderRadius: 2,
            fontFamily: 'monospace',
          }}>
            {task.assigned_to}
          </span>
        )}

        {/* MARKER_130.C18B: Commit hash */}
        {task.commit_hash && (
          <span style={{
            fontSize: 9,
            color: '#555',
            fontFamily: 'monospace',
            letterSpacing: 0.3,
          }}>
            {task.commit_hash.slice(0, 8)}
          </span>
        )}

        {/* Status indicator — CSS, no emoji */}
        <StatusIndicator status={task.status} />

        {/* MARKER_128.3B: Result lifecycle badge */}
        {localResultStatus && RESULT_STATUS_STYLE[localResultStatus] && (
          <span style={{
            background: RESULT_STATUS_STYLE[localResultStatus].bg,
            color: RESULT_STATUS_STYLE[localResultStatus].color,
            fontSize: 8,
            padding: '1px 4px',
            borderRadius: 2,
            fontFamily: 'monospace',
            marginLeft: 4,
          }}>
            {RESULT_STATUS_STYLE[localResultStatus].label}
          </span>
        )}
      </div>

      {/* Expanded view */}
      {expanded && (
        <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          {/* Description */}
          {task.description && task.description !== task.title && (
            <div style={{ fontSize: 11, color: '#777', marginBottom: 6, lineHeight: 1.4 }}>
              {task.description.slice(0, 200)}
              {task.description.length > 200 && '...'}
            </div>
          )}

          {/* Tags — monochrome pills */}
          {task.tags && task.tags.length > 0 && (
            <div style={{ display: 'flex', gap: 4, marginBottom: 6, flexWrap: 'wrap' }}>
              {task.tags.map((tag) => (
                <span
                  key={tag}
                  style={{
                    fontSize: 9,
                    background: 'rgba(255,255,255,0.06)',
                    color: '#888',
                    padding: '1px 6px',
                    borderRadius: 2,
                    fontFamily: 'monospace',
                    letterSpacing: 0.3,
                  }}
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Meta info */}
          <div style={{ fontSize: 10, color: '#555', marginBottom: 6, fontFamily: 'monospace' }}>
            {task.source && `src:${task.source}`}
            {task.preset && ` · ${task.preset}`}
            {task.created_at && ` · ${new Date(task.created_at).toLocaleTimeString()}`}
          </div>

          {/* Actions — dark monochrome buttons */}
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
                  background: '#1a1a1a',
                  color: '#888',
                  border: '1px solid #333',
                  borderRadius: 3,
                  fontSize: 10,
                  fontFamily: 'monospace',
                  padding: '2px 4px',
                  outline: 'none',
                }}
              >
                <option value="1">P1</option>
                <option value="2">P2</option>
                <option value="3">P3</option>
                <option value="4">P4</option>
                <option value="5">P5</option>
              </select>
            )}

            {/* MARKER_128.5A: Run button with preset selector */}
            {onDispatch && isDispatchable && (
              <>
                {/* MARKER_128.5C: Preset selector dropdown */}
                <select
                  value={selectedPreset}
                  onChange={(e) => {
                    e.stopPropagation();
                    setSelectedPreset(e.target.value);
                  }}
                  onClick={(e) => e.stopPropagation()}
                  style={{
                    background: '#1a1a1a',
                    color: '#666',
                    border: '1px solid #333',
                    borderRadius: 3,
                    fontSize: 9,
                    fontFamily: 'monospace',
                    padding: '2px 4px',
                    outline: 'none',
                  }}
                >
                  <option value="dragon_bronze">bronze</option>
                  <option value="dragon_silver">silver</option>
                  <option value="dragon_gold">gold</option>
                </select>
                {/* Run button — Nolan blue-gray accent */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDispatch(task.id, selectedPreset);
                  }}
                  style={{
                    background: '#2d3d5a',
                    color: '#8af',
                    border: '1px solid #3d4d6a',
                    borderRadius: 3,
                    fontSize: 10,
                    fontFamily: 'monospace',
                    padding: '3px 10px',
                    cursor: 'pointer',
                    letterSpacing: 0.5,
                    transition: 'all 0.15s',
                  }}
                >
                  ▶ run
                </button>
              </>
            )}

            {/* MARKER_126.5G: Stop button for running tasks */}
            {onCancel && task.status === 'running' && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onCancel(task.id);
                }}
                style={{
                  background: 'rgba(160,80,80,0.15)',
                  color: '#c88',
                  border: '1px solid rgba(160,80,80,0.3)',
                  borderRadius: 3,
                  fontSize: 10,
                  fontFamily: 'monospace',
                  padding: '3px 10px',
                  cursor: 'pointer',
                  letterSpacing: 0.5,
                  textTransform: 'uppercase',
                  transition: 'all 0.15s',
                }}
              >
                stop
              </button>
            )}

            {/* MARKER_127.0B: View Results button for done/failed tasks */}
            {hasPipelineResults && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  fetchResults();
                }}
                disabled={resultsLoading}
                style={{
                  background: showResults ? '#2a2a2a' : '#1a1a1a',
                  color: showResults ? '#e0e0e0' : '#888',
                  border: `1px solid ${showResults ? '#444' : '#333'}`,
                  borderRadius: 3,
                  fontSize: 10,
                  fontFamily: 'monospace',
                  padding: '3px 10px',
                  cursor: resultsLoading ? 'wait' : 'pointer',
                  letterSpacing: 0.5,
                  transition: 'all 0.15s',
                }}
              >
                {resultsLoading ? '...' : showResults ? 'hide' : 'results'}
              </button>
            )}

            {/* Remove button — subtle */}
            {onRemove && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRemove(task.id);
                }}
                style={{
                  background: 'transparent',
                  color: '#444',
                  border: '1px solid #333',
                  borderRadius: 3,
                  fontSize: 10,
                  padding: '2px 6px',
                  cursor: 'pointer',
                  marginLeft: 'auto',
                  transition: 'color 0.15s',
                }}
              >
                ✕
              </button>
            )}
          </div>

          {/* MARKER_127.0B: Pipeline Results Display */}
          {showResults && results && (
            <div style={{ marginTop: 10, paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
              {resultsError && (
                <div style={{ color: '#a66', fontSize: 10, marginBottom: 6 }}>{resultsError}</div>
              )}

              {results.message && (
                <div style={{ color: '#666', fontSize: 10, marginBottom: 6, fontStyle: 'italic' }}>
                  {results.message}
                </div>
              )}

              {results.subtasks.length > 0 && (
                <div>
                  {/* MARKER_128.8A: Header with Apply All button */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontSize: 9, color: '#555', letterSpacing: 0.5, textTransform: 'uppercase' }}>
                      subtasks ({results.subtasks.length})
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        applyAllResults();
                      }}
                      disabled={applyingAll || !results.subtasks.some(st => st.result && st.status === 'done')}
                      style={{
                        background: applyingAll ? '#333' : '#2d5a2d',
                        color: applyingAll ? '#888' : '#8a8',
                        border: '1px solid #3a6a3a',
                        borderRadius: 2,
                        fontSize: 9,
                        padding: '2px 8px',
                        cursor: applyingAll ? 'wait' : 'pointer',
                        fontFamily: 'monospace',
                      }}
                    >
                      {applyingAll && applyAllProgress
                        ? `applying ${applyAllProgress.current}/${applyAllProgress.total}...`
                        : 'apply all'}
                    </button>
                  </div>
                  {results.subtasks.map((st, idx) => (
                    <div key={idx} style={{ marginBottom: 6 }}>
                      {/* Subtask header — clickable to expand */}
                      {/* MARKER_C23A: Enhanced with RALF loop metrics */}
                      <div
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedSubtask(expandedSubtask === idx ? null : idx);
                        }}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 6,
                          padding: '4px 6px',
                          background: 'rgba(255,255,255,0.02)',
                          borderRadius: 2,
                          cursor: st.result ? 'pointer' : 'default',
                        }}
                      >
                        {/* MARKER_C23A: Status icon with RALF awareness */}
                        <span style={{
                          color: st.verifier_feedback?.escalated
                            ? '#a66'  // Escalated = red
                            : st.status === 'done'
                              ? '#8a8'  // Done = green
                              : '#a66', // Failed = red
                          fontSize: 10
                        }}>
                          {st.verifier_feedback?.escalated ? '🚫' : st.status === 'done' ? '✓' : '✕'}
                        </span>

                        <span style={{ flex: 1, color: '#888', fontSize: 10 }}>
                          {st.description}
                        </span>

                        {/* MARKER_C23A: RALF score display */}
                        {st.verifier_feedback && (
                          <span style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4,
                            fontSize: 9,
                            fontFamily: 'monospace',
                          }}>
                            {/* Confidence score */}
                            <span style={{
                              color: st.verifier_feedback.confidence >= 0.7
                                ? '#8a8'  // Good = green
                                : st.verifier_feedback.confidence >= 0.5
                                  ? '#aa8'  // Warning = yellow
                                  : '#a66',  // Bad = red
                              padding: '0 4px',
                              background: 'rgba(255,255,255,0.03)',
                              borderRadius: 2,
                            }}>
                              {(st.verifier_feedback.confidence * 100).toFixed(0)}%
                            </span>

                            {/* Retry count if > 1 */}
                            {(st.verifier_feedback.retry_count || 0) > 0 && (
                              <span style={{ color: '#666' }}>
                                ({st.verifier_feedback.retry_count}/{st.verifier_feedback.max_retries || 3})
                              </span>
                            )}

                            {/* Escalated badge */}
                            {st.verifier_feedback.escalated && (
                              <span style={{
                                color: '#a66',
                                background: 'rgba(160,80,80,0.15)',
                                padding: '0 4px',
                                borderRadius: 2,
                                fontSize: 8,
                              }}>
                                escalated
                              </span>
                            )}
                          </span>
                        )}

                        {st.marker && (
                          <span style={{ color: '#444', fontSize: 9, fontFamily: 'monospace' }}>
                            {st.marker}
                          </span>
                        )}
                        {st.result && (
                          <span style={{ color: '#555', fontSize: 9 }}>
                            {expandedSubtask === idx ? '▼' : '▸'}
                          </span>
                        )}
                      </div>

                      {/* Subtask result — code block or diff */}
                      {expandedSubtask === idx && st.result && (
                        <div style={{ marginTop: 4, position: 'relative' }}>
                          {/* MARKER_128.4B: View mode tabs */}
                          <div style={{
                            display: 'flex',
                            gap: 2,
                            marginBottom: 4,
                          }}>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setSubtaskViewMode(prev => ({ ...prev, [idx]: 'code' }));
                              }}
                              style={{
                                background: (subtaskViewMode[idx] || 'code') === 'code' ? '#333' : '#1a1a1a',
                                color: (subtaskViewMode[idx] || 'code') === 'code' ? '#ccc' : '#555',
                                border: '1px solid #333',
                                borderRadius: '2px 2px 0 0',
                                fontSize: 9,
                                padding: '2px 8px',
                                cursor: 'pointer',
                                fontFamily: 'monospace',
                              }}
                            >
                              code
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setSubtaskViewMode(prev => ({ ...prev, [idx]: 'diff' }));
                              }}
                              disabled={!st.diff_patch}
                              style={{
                                background: subtaskViewMode[idx] === 'diff' ? '#333' : '#1a1a1a',
                                color: !st.diff_patch ? '#333' : subtaskViewMode[idx] === 'diff' ? '#ccc' : '#555',
                                border: '1px solid #333',
                                borderRadius: '2px 2px 0 0',
                                fontSize: 9,
                                padding: '2px 8px',
                                cursor: st.diff_patch ? 'pointer' : 'not-allowed',
                                fontFamily: 'monospace',
                              }}
                              title={!st.diff_patch ? 'No diff available' : 'View diff'}
                            >
                              diff
                            </button>
                            <div style={{ flex: 1 }} />
                            {/* MARKER_128.2C: Copy + Apply buttons */}
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                navigator.clipboard.writeText(st.result || '');
                              }}
                              style={{
                                background: '#333',
                                color: '#888',
                                border: '1px solid #444',
                                borderRadius: 2,
                                fontSize: 9,
                                padding: '2px 6px',
                                cursor: 'pointer',
                              }}
                            >
                              copy
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                applySubtask(idx);
                              }}
                              disabled={applyingSubtask === idx}
                              style={{
                                background: '#2d5a2d',
                                color: '#8a8',
                                border: '1px solid #3a6a3a',
                                borderRadius: 2,
                                fontSize: 9,
                                padding: '2px 6px',
                                cursor: applyingSubtask === idx ? 'wait' : 'pointer',
                              }}
                            >
                              {applyingSubtask === idx ? '...' : 'apply'}
                            </button>
                          </div>
                          {/* Apply result message */}
                          {applyResult && applyResult.idx === idx && (
                            <div style={{
                              background: applyResult.success ? '#2d5a2d' : '#5a2d2d',
                              color: applyResult.success ? '#8a8' : '#a88',
                              fontSize: 8,
                              padding: '2px 6px',
                              borderRadius: 2,
                              marginBottom: 4,
                            }}>
                              {applyResult.message}
                            </div>
                          )}
                          {/* MARKER_128.4B: Conditional render — diff or code */}
                          {subtaskViewMode[idx] === 'diff' && st.diff_patch ? (
                            <DiffViewer diff={st.diff_patch} maxHeight={300} />
                          ) : (
                            <pre style={{
                              background: '#181818',
                              color: '#d0d0d0',
                              padding: '8px 10px',
                              borderRadius: 3,
                              fontSize: 10,
                              fontFamily: 'monospace',
                              overflow: 'auto',
                              maxHeight: 300,
                              whiteSpace: 'pre-wrap',
                              wordBreak: 'break-word',
                              margin: 0,
                              border: '1px solid #222',
                            }}>
                              {st.result}
                            </pre>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {results.results_summary && Object.keys(results.results_summary).length > 0 && (
                <div style={{ marginTop: 8, fontSize: 9, color: '#555', fontFamily: 'monospace' }}>
                  completed: {(results.results_summary as Record<string, number>).subtasks_completed || 0}/
                  {(results.results_summary as Record<string, number>).subtasks_total || 0}
                </div>
              )}

              {/* MARKER_128.3C: Result lifecycle action buttons */}
              <div style={{
                marginTop: 10,
                paddingTop: 8,
                borderTop: '1px solid rgba(255,255,255,0.06)',
                display: 'flex',
                gap: 6,
                alignItems: 'center',
              }}>
                <span style={{ fontSize: 9, color: '#555', marginRight: 4 }}>mark as:</span>
                <button
                  onClick={(e) => { e.stopPropagation(); updateResultStatus('applied'); }}
                  disabled={localResultStatus === 'applied'}
                  style={{
                    background: localResultStatus === 'applied' ? '#2d5a2d' : 'transparent',
                    color: localResultStatus === 'applied' ? '#8a8' : '#686',
                    border: '1px solid #3a5a3a',
                    borderRadius: 2,
                    fontSize: 9,
                    padding: '2px 8px',
                    cursor: localResultStatus === 'applied' ? 'default' : 'pointer',
                    fontFamily: 'monospace',
                  }}
                >
                  applied
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); updateResultStatus('rejected'); }}
                  disabled={localResultStatus === 'rejected'}
                  style={{
                    background: localResultStatus === 'rejected' ? '#5a2d2d' : 'transparent',
                    color: localResultStatus === 'rejected' ? '#a88' : '#866',
                    border: '1px solid #5a3a3a',
                    borderRadius: 2,
                    fontSize: 9,
                    padding: '2px 8px',
                    cursor: localResultStatus === 'rejected' ? 'default' : 'pointer',
                    fontFamily: 'monospace',
                  }}
                >
                  rejected
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); updateResultStatus('rework'); }}
                  disabled={localResultStatus === 'rework'}
                  style={{
                    background: localResultStatus === 'rework' ? '#5a4a2d' : 'transparent',
                    color: localResultStatus === 'rework' ? '#aa8' : '#886',
                    border: '1px solid #5a4a3a',
                    borderRadius: 2,
                    fontSize: 9,
                    padding: '2px 8px',
                    cursor: localResultStatus === 'rework' ? 'default' : 'pointer',
                    fontFamily: 'monospace',
                  }}
                >
                  rework
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
});
