/**
 * MARKER_143.P4: PipelineResultsViewer — standalone pipeline results display.
 * Extracted from TaskCard's inline results viewer (was ~300 lines).
 * Shows subtask list with code/diff tabs, apply buttons, RALF scores.
 *
 * @phase 143
 * @status active
 */
import { useState, useCallback, useEffect } from 'react';
import { DiffViewer } from '../panels/DiffViewer';
import { NOLAN_PALETTE } from '../../utils/dagLayout';

const API_BASE = 'http://localhost:5001/api/debug';

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
  diff_patch?: string;
  original_file?: string;
  verifier_feedback?: VerifierFeedback;
}

interface PipelineResults {
  success: boolean;
  task_id: string;
  subtasks: SubtaskResult[];
  results_summary?: Record<string, unknown>;
  message?: string;
}

interface PipelineResultsViewerProps {
  taskId: string;
}

export function PipelineResultsViewer({ taskId }: PipelineResultsViewerProps) {
  const [results, setResults] = useState<PipelineResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSubtask, setExpandedSubtask] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<Record<number, 'code' | 'diff'>>({});
  const [applyingSubtask, setApplyingSubtask] = useState<number | null>(null);
  const [applyResult, setApplyResult] = useState<{ idx: number; success: boolean; message: string } | null>(null);
  const [applyingAll, setApplyingAll] = useState(false);
  const [applyAllProgress, setApplyAllProgress] = useState<{ current: number; total: number } | null>(null);
  const [resultStatus, setResultStatus] = useState<'applied' | 'rejected' | 'rework' | null>(null);

  // Fetch results on mount or taskId change
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setResults(null);
    setExpandedSubtask(null);

    fetch(`${API_BASE}/pipeline-results/${taskId}`)
      .then(r => r.json())
      .then(data => {
        if (cancelled) return;
        if (data.success) {
          setResults(data);
        } else {
          setError(data.error || data.message || 'No results');
        }
      })
      .catch(err => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [taskId]);

  // Apply single subtask
  const applySubtask = useCallback(async (idx: number) => {
    setApplyingSubtask(idx);
    setApplyResult(null);
    try {
      const res = await fetch(`${API_BASE}/pipeline-results/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: taskId, subtask_idx: idx }),
      });
      const data = await res.json();
      setApplyResult({
        idx,
        success: data.success,
        message: data.success ? `Applied: ${data.files_written?.join(', ')}` : (data.error || 'Failed'),
      });
    } catch (err: any) {
      setApplyResult({ idx, success: false, message: err.message });
    } finally {
      setApplyingSubtask(null);
    }
  }, [taskId]);

  // Apply all subtasks
  const applyAllResults = useCallback(async () => {
    if (!results?.subtasks || applyingAll) return;
    const subs = results.subtasks.map((st, idx) => ({ st, idx })).filter(({ st }) => st.result && st.status === 'done');
    if (subs.length === 0) return;

    setApplyingAll(true);
    let ok = 0;
    for (let i = 0; i < subs.length; i++) {
      setApplyAllProgress({ current: i + 1, total: subs.length });
      try {
        const res = await fetch(`${API_BASE}/pipeline-results/apply`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ task_id: taskId, subtask_idx: subs[i].idx }),
        });
        const data = await res.json();
        if (data.success) ok++;
      } catch { /* continue */ }
    }
    setApplyingAll(false);
    setApplyAllProgress(null);
    if (ok === subs.length) updateResultStatus('applied');
  }, [results, taskId, applyingAll]);

  // Update result lifecycle status
  const updateResultStatus = useCallback(async (status: 'applied' | 'rejected' | 'rework') => {
    try {
      const res = await fetch(`${API_BASE}/pipeline-results/${taskId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      const data = await res.json();
      if (data.success) setResultStatus(status);
    } catch (err) {
      console.error('Failed to update result status:', err);
    }
  }, [taskId]);

  if (loading) {
    return <div style={{ color: '#555', fontSize: 10, padding: 12 }}>Loading results...</div>;
  }

  if (error) {
    return <div style={{ color: '#a66', fontSize: 10, padding: 12 }}>{error}</div>;
  }

  if (!results) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {results.message && (
        <div style={{ color: '#666', fontSize: 9, fontStyle: 'italic' }}>{results.message}</div>
      )}

      {/* Subtasks header + Apply All */}
      {results.subtasks.length > 0 && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 9, color: '#555', letterSpacing: 0.5, textTransform: 'uppercase' }}>
              subtasks ({results.subtasks.length})
            </span>
            <button
              onClick={applyAllResults}
              disabled={applyingAll || !results.subtasks.some(st => st.result && st.status === 'done')}
              style={{
                background: applyingAll ? '#333' : '#2d5a2d',
                color: applyingAll ? '#888' : '#8a8',
                border: '1px solid #3a6a3a',
                borderRadius: 2, fontSize: 8, padding: '2px 6px',
                cursor: applyingAll ? 'wait' : 'pointer', fontFamily: 'monospace',
              }}
            >
              {applyingAll && applyAllProgress
                ? `${applyAllProgress.current}/${applyAllProgress.total}...`
                : 'apply all'}
            </button>
          </div>

          {/* Subtask list */}
          {results.subtasks.map((st, idx) => (
            <div key={idx}>
              {/* Subtask header */}
              <div
                onClick={() => setExpandedSubtask(expandedSubtask === idx ? null : idx)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 4,
                  padding: '3px 6px', background: 'rgba(255,255,255,0.02)',
                  borderRadius: 2, cursor: st.result ? 'pointer' : 'default',
                }}
              >
                <span style={{
                  color: st.verifier_feedback?.escalated ? '#a66' : st.status === 'done' ? '#8a8' : '#a66',
                  fontSize: 9,
                }}>{st.status === 'done' ? '✓' : '✕'}</span>

                <span style={{ flex: 1, color: '#888', fontSize: 9, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {st.description}
                </span>

                {st.verifier_feedback && (
                  <span style={{
                    fontSize: 8, fontFamily: 'monospace',
                    color: st.verifier_feedback.confidence >= 0.7 ? '#8a8' : st.verifier_feedback.confidence >= 0.5 ? '#aa8' : '#a66',
                    padding: '0 3px', background: 'rgba(255,255,255,0.03)', borderRadius: 2,
                  }}>{(st.verifier_feedback.confidence * 100).toFixed(0)}%</span>
                )}

                {st.result && (
                  <span style={{ color: '#555', fontSize: 8 }}>{expandedSubtask === idx ? '▼' : '▸'}</span>
                )}
              </div>

              {/* Expanded subtask */}
              {expandedSubtask === idx && st.result && (
                <div style={{ marginTop: 4, marginLeft: 8 }}>
                  {/* Code/diff tabs + actions */}
                  <div style={{ display: 'flex', gap: 2, marginBottom: 3 }}>
                    <button
                      onClick={() => setViewMode(p => ({ ...p, [idx]: 'code' }))}
                      style={{
                        background: (viewMode[idx] || 'code') === 'code' ? '#333' : '#1a1a1a',
                        color: (viewMode[idx] || 'code') === 'code' ? '#ccc' : '#555',
                        border: '1px solid #333', borderRadius: '2px 2px 0 0',
                        fontSize: 8, padding: '2px 6px', cursor: 'pointer', fontFamily: 'monospace',
                      }}
                    >code</button>
                    <button
                      onClick={() => setViewMode(p => ({ ...p, [idx]: 'diff' }))}
                      disabled={!st.diff_patch}
                      style={{
                        background: viewMode[idx] === 'diff' ? '#333' : '#1a1a1a',
                        color: !st.diff_patch ? '#333' : viewMode[idx] === 'diff' ? '#ccc' : '#555',
                        border: '1px solid #333', borderRadius: '2px 2px 0 0',
                        fontSize: 8, padding: '2px 6px', cursor: st.diff_patch ? 'pointer' : 'not-allowed', fontFamily: 'monospace',
                      }}
                    >diff</button>
                    <div style={{ flex: 1 }} />
                    <button
                      onClick={() => navigator.clipboard.writeText(st.result || '')}
                      style={{
                        background: '#333', color: '#888', border: '1px solid #444',
                        borderRadius: 2, fontSize: 8, padding: '2px 5px', cursor: 'pointer',
                      }}
                    >copy</button>
                    <button
                      onClick={() => applySubtask(idx)}
                      disabled={applyingSubtask === idx}
                      style={{
                        background: '#2d5a2d', color: '#8a8', border: '1px solid #3a6a3a',
                        borderRadius: 2, fontSize: 8, padding: '2px 5px',
                        cursor: applyingSubtask === idx ? 'wait' : 'pointer',
                      }}
                    >{applyingSubtask === idx ? '...' : 'apply'}</button>
                  </div>

                  {applyResult && applyResult.idx === idx && (
                    <div style={{
                      background: applyResult.success ? '#2d5a2d' : '#5a2d2d',
                      color: applyResult.success ? '#8a8' : '#a88',
                      fontSize: 8, padding: '2px 6px', borderRadius: 2, marginBottom: 3,
                    }}>{applyResult.message}</div>
                  )}

                  {viewMode[idx] === 'diff' && st.diff_patch ? (
                    <DiffViewer diff={st.diff_patch} maxHeight={250} />
                  ) : (
                    <pre style={{
                      background: '#181818', color: '#d0d0d0', padding: '6px 8px',
                      borderRadius: 2, fontSize: 9, fontFamily: 'monospace',
                      overflow: 'auto', maxHeight: 250, whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word', margin: 0, border: '1px solid #222',
                    }}>{st.result}</pre>
                  )}
                </div>
              )}
            </div>
          ))}
        </>
      )}

      {/* Result lifecycle buttons */}
      <div style={{
        marginTop: 6, paddingTop: 6,
        borderTop: `1px solid ${NOLAN_PALETTE.borderDim}`,
        display: 'flex', gap: 4, alignItems: 'center',
      }}>
        <span style={{ fontSize: 8, color: '#555' }}>mark:</span>
        {(['applied', 'rejected', 'rework'] as const).map(status => {
          const colors = {
            applied: { bg: '#2d5a2d', color: '#8a8', border: '#3a5a3a' },
            rejected: { bg: '#5a2d2d', color: '#a88', border: '#5a3a3a' },
            rework: { bg: '#5a4a2d', color: '#aa8', border: '#5a4a3a' },
          };
          const c = colors[status];
          const isActive = resultStatus === status;
          return (
            <button
              key={status}
              onClick={() => updateResultStatus(status)}
              disabled={isActive}
              style={{
                background: isActive ? c.bg : 'transparent',
                color: isActive ? c.color : '#666',
                border: `1px solid ${c.border}`,
                borderRadius: 2, fontSize: 8, padding: '2px 6px',
                cursor: isActive ? 'default' : 'pointer', fontFamily: 'monospace',
              }}
            >{status}</button>
          );
        })}
      </div>
    </div>
  );
}
