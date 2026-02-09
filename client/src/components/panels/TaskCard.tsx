/**
 * MARKER_126.2A: TaskCard — Nolan dark style, no emoji.
 * MARKER_127.0B: Results Viewer — expand to see pipeline results/code
 * MARKER_128.2C: Apply button — write code to disk
 * MARKER_128.3B/C: Result lifecycle badges + action buttons
 * CSS-only status indicators, monochrome priority, glassmorphism accents.
 * Phase 128.3: Style upgrade — "Batman Nolan, not Burton"
 *
 * @status active
 * @phase 128.3
 * @depends react
 * @used_by DevPanel
 */

import { useState, useCallback } from 'react';

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
}

// MARKER_127.0B: Pipeline results data structure
interface SubtaskResult {
  description: string;
  status: string;
  result?: string;
  marker?: string;
  needs_research?: boolean;
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
  onPriorityChange?: (taskId: string, priority: number) => void;
  onRemove?: (taskId: string) => void;
  onDispatch?: (taskId: string) => void;
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
export function TaskCard({ task, onPriorityChange, onRemove, onDispatch, onCancel }: TaskCardProps) {
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

  // MARKER_128.3B: Local result status (synced from props)
  const [localResultStatus, setLocalResultStatus] = useState(task.result_status);

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
        background: hover
          ? 'rgba(255,255,255,0.04)'
          : expanded
            ? 'rgba(255,255,255,0.03)'
            : 'rgba(255,255,255,0.015)',
        borderRadius: 4,
        borderLeft: `2px solid ${prio.bg}`,
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        backdropFilter: hover ? 'blur(2px)' : 'none',
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

            {/* Dispatch button — Nolan minimal */}
            {onDispatch && isDispatchable && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDispatch(task.id);
                }}
                style={{
                  background: '#222',
                  color: '#e0e0e0',
                  border: '1px solid #444',
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
                run
              </button>
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
                  <div style={{ fontSize: 9, color: '#555', marginBottom: 6, letterSpacing: 0.5, textTransform: 'uppercase' }}>
                    subtasks ({results.subtasks.length})
                  </div>
                  {results.subtasks.map((st, idx) => (
                    <div key={idx} style={{ marginBottom: 6 }}>
                      {/* Subtask header — clickable to expand */}
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
                        <span style={{ color: st.status === 'done' ? '#8a8' : '#a66', fontSize: 10 }}>
                          {st.status === 'done' ? '✓' : '✕'}
                        </span>
                        <span style={{ flex: 1, color: '#888', fontSize: 10 }}>
                          {st.description}
                        </span>
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

                      {/* Subtask result — code block */}
                      {expandedSubtask === idx && st.result && (
                        <div style={{ marginTop: 4, position: 'relative' }}>
                          {/* MARKER_128.2C: Copy + Apply buttons */}
                          <div style={{ position: 'absolute', top: 4, right: 4, display: 'flex', gap: 4, zIndex: 1 }}>
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
                              position: 'absolute',
                              top: 26,
                              right: 4,
                              background: applyResult.success ? '#2d5a2d' : '#5a2d2d',
                              color: applyResult.success ? '#8a8' : '#a88',
                              fontSize: 8,
                              padding: '2px 6px',
                              borderRadius: 2,
                              maxWidth: 200,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              zIndex: 1,
                            }}>
                              {applyResult.message}
                            </div>
                          )}
                          <pre style={{
                            background: '#181818',
                            color: '#d0d0d0',
                            padding: '8px 10px',
                            paddingTop: 24,
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
}
