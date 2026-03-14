/**
 * MARKER_C23C: ArtifactViewer — Pipeline artifact staging and approval.
 * MARKER_136.W2A: Added disk artifacts section for completed pipeline outputs.
 * Shows pending artifacts from Dragon pipeline with approve/reject buttons.
 * Style: Nolan monochrome.
 *
 * @status active
 * @phase 136
 * @depends react
 * @used_by DevPanel
 */

import { useState, useEffect, useCallback } from 'react';

interface Artifact {
  id?: string;
  path?: string;
  type?: string;
  language?: string;
  content?: string;
  line_count?: number;
}

// MARKER_136.W2A: Disk artifact interface
interface DiskArtifact {
  name: string;
  filename: string;
  path: string;
  size: number;
  modified: string;
  extension: string;
}

interface ApprovalRequest {
  id: string;
  workflow_id: string;
  artifacts: Artifact[];
  eval_score: number;
  eval_feedback: string;
  status: string;
  created_at: string;
}

interface PanelArtifact {
  id: string;
  name: string;
  status: string;
  artifact_type: string;
  language: string;
  file_path: string;
  size_bytes: number;
  modified_at?: number;
}

interface FeedbackReportSummary {
  run_id: string;
  task: string;
  quality_score?: number;
  issues_count?: number;
  improvements_count?: number;
  preset?: string;
  status?: string;
  duration_s?: number;
  saved_at?: string;
}

const API_BASE = 'http://localhost:5001/api/approvals';
const DEBUG_API = 'http://localhost:5001/api/debug';  // MARKER_136.W2A
const ARTIFACTS_API = 'http://localhost:5001/api/artifacts';
const FEEDBACK_API = 'http://localhost:5001/api/feedback';

// Nolan palette
const COLORS = {
  bg: '#111',
  bgLight: '#1a1a1a',
  border: '#222',
  borderLight: '#333',
  text: '#e0e0e0',
  textMuted: '#888',
  textDim: '#666',
  success: '#2a3a2a',
  successText: '#6a8a6a',
  error: '#3a2a2a',
  errorText: '#8a6a6a',
};

export function ArtifactViewer() {
  const [pending, setPending] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedArtifact, setExpandedArtifact] = useState<string | null>(null);
  const [actionPending, setActionPending] = useState<string | null>(null);

  // MARKER_136.W2A: Disk artifacts state
  const [diskArtifacts, setDiskArtifacts] = useState<DiskArtifact[]>([]);
  const [expandedDiskArtifact, setExpandedDiskArtifact] = useState<string | null>(null);
  const [diskArtifactContent, setDiskArtifactContent] = useState<Record<string, string>>({});
  // MARKER_139.MCC_ARTIFACTS_REAL_DATA: Real artifact sources for vetka_out + feedback reports
  const [panelArtifacts, setPanelArtifacts] = useState<PanelArtifact[]>([]);
  const [expandedPanelArtifact, setExpandedPanelArtifact] = useState<string | null>(null);
  const [feedbackReports, setFeedbackReports] = useState<FeedbackReportSummary[]>([]);
  const [expandedReport, setExpandedReport] = useState<string | null>(null);
  const [reportContent, setReportContent] = useState<Record<string, string>>({});
  // MARKER_141.PANEL_ARTIFACT_CONTENT: Content cache for panel artifacts
  const [panelArtifactContent, setPanelArtifactContent] = useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = useState<'pending' | 'completed'>('pending');

  const fetchPending = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/pending`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.success) {
        setPending(data.pending || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fetch failed');
    } finally {
      setLoading(false);
    }
  }, []);

  // MARKER_136.W2A: Fetch disk artifacts
  const fetchDiskArtifacts = useCallback(async () => {
    try {
      const res = await fetch(`${DEBUG_API}/artifacts`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.success) {
        setDiskArtifacts(data.artifacts || []);
      }
    } catch (err) {
      console.error('[ArtifactViewer] Failed to fetch disk artifacts:', err);
    }
  }, []);

  const fetchPanelArtifacts = useCallback(async () => {
    try {
      const res = await fetch(ARTIFACTS_API);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.success) {
        setPanelArtifacts(data.artifacts || []);
      }
    } catch (err) {
      console.error('[ArtifactViewer] Failed to fetch /api/artifacts:', err);
    }
  }, []);

  const fetchFeedbackReports = useCallback(async () => {
    try {
      const res = await fetch(`${FEEDBACK_API}/reports?limit=20`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.success) {
        setFeedbackReports(data.reports || []);
      }
    } catch (err) {
      console.error('[ArtifactViewer] Failed to fetch feedback reports:', err);
    }
  }, []);

  // MARKER_136.W2A: Load artifact content on demand
  const loadDiskArtifactContent = useCallback(async (filename: string) => {
    if (diskArtifactContent[filename]) return;
    try {
      const res = await fetch(`${DEBUG_API}/artifacts/${encodeURIComponent(filename)}`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.success && data.artifact?.content) {
        setDiskArtifactContent(prev => ({ ...prev, [filename]: data.artifact.content }));
      }
    } catch (err) {
      console.error('[ArtifactViewer] Failed to load artifact content:', err);
    }
  }, [diskArtifactContent]);

  const loadFeedbackReportContent = useCallback(async (runId: string) => {
    if (reportContent[runId]) return;
    try {
      const res = await fetch(`${FEEDBACK_API}/reports/${encodeURIComponent(runId)}`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.success && data.report) {
        setReportContent(prev => ({
          ...prev,
          [runId]: JSON.stringify(data.report, null, 2),
        }));
      }
    } catch (err) {
      console.error('[ArtifactViewer] Failed to load report content:', err);
    }
  }, [reportContent]);

  // MARKER_141.PANEL_ARTIFACT_CONTENT: Load panel artifact content on demand
  const loadPanelArtifactContent = useCallback(async (artifactId: string) => {
    if (panelArtifactContent[artifactId]) return;
    try {
      const res = await fetch(`${ARTIFACTS_API}/${encodeURIComponent(artifactId)}/content`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.success && data.content) {
        setPanelArtifactContent(prev => ({ ...prev, [artifactId]: data.content }));
      }
    } catch (err) {
      console.error('[ArtifactViewer] Failed to load panel artifact content:', err);
    }
  }, [panelArtifactContent]);

  // MARKER_145.CLEANUP: Fetch once on mount only — no polling.
  // Was: 10s interval × 4 fetches = 34,560 API calls/day.
  // Refresh happens on user actions (approve/reject) below.
  useEffect(() => {
    fetchPending();
    fetchDiskArtifacts();
    fetchPanelArtifacts();
    fetchFeedbackReports();
  }, [fetchPending, fetchDiskArtifacts, fetchPanelArtifacts, fetchFeedbackReports]);

  const handleApprove = useCallback(async (requestId: string) => {
    setActionPending(requestId);
    try {
      const res = await fetch(`${API_BASE}/${requestId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'Approved via DevPanel' }),
      });
      const data = await res.json();
      if (data.success) {
        fetchPending();
      }
    } catch (err) {
      console.error('Approve failed:', err);
    } finally {
      setActionPending(null);
    }
  }, [fetchPending]);

  const handleReject = useCallback(async (requestId: string) => {
    const reason = prompt('Rejection reason:');
    if (!reason) return;

    setActionPending(requestId);
    try {
      const res = await fetch(`${API_BASE}/${requestId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      });
      const data = await res.json();
      if (data.success) {
        fetchPending();
      }
    } catch (err) {
      console.error('Reject failed:', err);
    } finally {
      setActionPending(null);
    }
  }, [fetchPending]);

  const formatScore = (score: number) => {
    return `${Math.round(score * 100)}%`;
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return COLORS.successText;
    if (score >= 0.6) return '#aa8';
    return COLORS.errorText;
  };

  const completedCount = diskArtifacts.length + panelArtifacts.length + feedbackReports.length;

  return (
    <div style={{
      padding: 0,
      fontSize: 11,
      color: COLORS.text,
      fontFamily: 'monospace',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
    }}>
      {/* MARKER_136.W2A: Tabs for pending/completed */}
      <div style={{
        display: 'flex',
        gap: 0,
        marginBottom: 12,
        borderBottom: `1px solid ${COLORS.border}`,
      }}>
        <button
          onClick={() => setActiveTab('pending')}
          style={{
            flex: 1,
            padding: '8px 0',
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'pending' ? `1px solid ${COLORS.text}` : '1px solid transparent',
            color: activeTab === 'pending' ? COLORS.text : COLORS.textDim,
            fontSize: 10,
            fontFamily: 'monospace',
            fontWeight: activeTab === 'pending' ? 600 : 400,
            letterSpacing: 1,
            textTransform: 'uppercase',
            cursor: 'pointer',
          }}
        >
          pending ({pending.length})
        </button>
        <button
          onClick={() => setActiveTab('completed')}
          style={{
            flex: 1,
            padding: '8px 0',
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'completed' ? `1px solid ${COLORS.text}` : '1px solid transparent',
            color: activeTab === 'completed' ? COLORS.text : COLORS.textDim,
            fontSize: 10,
            fontFamily: 'monospace',
            fontWeight: activeTab === 'completed' ? 600 : 400,
            letterSpacing: 1,
            textTransform: 'uppercase',
            cursor: 'pointer',
          }}
        >
          completed ({completedCount})
        </button>
        <button
          onClick={() => { fetchPending(); fetchDiskArtifacts(); fetchPanelArtifacts(); fetchFeedbackReports(); }}
          disabled={loading}
          style={{
            padding: '4px 8px',
            background: 'transparent',
            border: 'none',
            color: loading ? COLORS.textDim : COLORS.textMuted,
            fontSize: 9,
            fontFamily: 'monospace',
            cursor: loading ? 'wait' : 'pointer',
          }}
        >
          {loading ? '...' : '↻'}
        </button>
      </div>

      {error && (
        <div style={{
          color: COLORS.errorText,
          marginBottom: 10,
          padding: '6px 8px',
          background: COLORS.error,
          borderRadius: 2,
          fontSize: 10
        }}>
          {error}
        </div>
      )}

      {/* Scrollable content */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        overflowX: 'hidden',
        minHeight: 0,
      }}>
        {/* MARKER_136.W2A: Pending tab content */}
        {activeTab === 'pending' && (
          <>
            {pending.length === 0 && !loading && (
              <div style={{ textAlign: 'center', color: COLORS.textDim, padding: 32, fontSize: 10 }}>
                no pending artifacts
              </div>
            )}

            {pending.map((request) => (
          <div key={request.id} style={{
            marginBottom: 12,
            padding: 10,
            background: 'rgba(255,255,255,0.02)',
            borderRadius: 4,
            border: `1px solid ${COLORS.border}`,
          }}>
            {/* Request header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span style={{ fontSize: 9, color: COLORS.textDim }}>
                {request.workflow_id?.slice(0, 12)}...
              </span>
              <span style={{
                fontSize: 9,
                padding: '1px 6px',
                background: 'rgba(255,255,255,0.04)',
                borderRadius: 2,
                color: getScoreColor(request.eval_score),
              }}>
                score: {formatScore(request.eval_score)}
              </span>
              <span style={{ flex: 1 }} />
              <span style={{ fontSize: 9, color: COLORS.textDim }}>
                {new Date(request.created_at).toLocaleTimeString()}
              </span>
            </div>

            {/* Eval feedback */}
            {request.eval_feedback && (
              <div style={{
                fontSize: 10,
                color: COLORS.textMuted,
                marginBottom: 10,
                padding: '6px 8px',
                background: 'rgba(255,255,255,0.02)',
                borderRadius: 2,
                lineHeight: 1.4,
              }}>
                {request.eval_feedback.slice(0, 200)}
                {request.eval_feedback.length > 200 && '...'}
              </div>
            )}

            {/* Artifacts list */}
            <div style={{ marginBottom: 10 }}>
              {request.artifacts.map((artifact, idx) => {
                const artifactKey = `${request.id}-${idx}`;
                const isExpanded = expandedArtifact === artifactKey;

                return (
                  <div key={idx} style={{
                    marginBottom: 6,
                    background: 'rgba(255,255,255,0.02)',
                    borderRadius: 3,
                    overflow: 'hidden',
                  }}>
                    {/* Artifact header */}
                    <div
                      onClick={() => setExpandedArtifact(isExpanded ? null : artifactKey)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        padding: '6px 8px',
                        cursor: 'pointer',
                        borderBottom: isExpanded ? `1px solid ${COLORS.border}` : 'none',
                      }}
                    >
                      <span style={{ color: '#555', fontSize: 10 }}>
                        {isExpanded ? '▼' : '▸'}
                      </span>
                      <span style={{ color: COLORS.text, fontSize: 10, flex: 1 }}>
                        {artifact.path || `Artifact ${idx + 1}`}
                      </span>
                      {artifact.language && (
                        <span style={{
                          fontSize: 8,
                          color: COLORS.textDim,
                          background: 'rgba(255,255,255,0.04)',
                          padding: '1px 4px',
                          borderRadius: 2,
                        }}>
                          {artifact.language}
                        </span>
                      )}
                      {artifact.line_count && (
                        <span style={{ fontSize: 8, color: COLORS.textDim }}>
                          {artifact.line_count} lines
                        </span>
                      )}
                    </div>

                    {/* Expanded content */}
                    {isExpanded && artifact.content && (
                      <div style={{ padding: 8 }}>
                        <pre style={{
                          background: '#181818',
                          color: '#d0d0d0',
                          padding: '8px 10px',
                          borderRadius: 3,
                          fontSize: 10,
                          fontFamily: 'monospace',
                          overflow: 'auto',
                          maxHeight: 200,
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word',
                          margin: 0,
                          border: '1px solid #222',
                        }}>
                          {artifact.content.slice(0, 2000)}
                          {(artifact.content?.length || 0) > 2000 && '\n... (truncated)'}
                        </pre>
                        <button
                          onClick={() => navigator.clipboard.writeText(artifact.content || '')}
                          style={{
                            marginTop: 6,
                            background: '#333',
                            color: COLORS.textMuted,
                            border: '1px solid #444',
                            borderRadius: 2,
                            fontSize: 9,
                            padding: '2px 8px',
                            cursor: 'pointer',
                          }}
                        >
                          copy
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Action buttons */}
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => handleApprove(request.id)}
                disabled={actionPending === request.id}
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                  padding: '8px 12px',
                  background: actionPending === request.id ? '#222' : COLORS.success,
                  color: COLORS.successText,
                  border: `1px solid ${COLORS.successText}`,
                  borderRadius: 3,
                  fontSize: 10,
                  fontFamily: 'monospace',
                  cursor: actionPending === request.id ? 'wait' : 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                ✓ Approve & Write
              </button>
              <button
                onClick={() => handleReject(request.id)}
                disabled={actionPending === request.id}
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                  padding: '8px 12px',
                  background: actionPending === request.id ? '#222' : COLORS.error,
                  color: COLORS.errorText,
                  border: `1px solid ${COLORS.errorText}`,
                  borderRadius: 3,
                  fontSize: 10,
                  fontFamily: 'monospace',
                  cursor: actionPending === request.id ? 'wait' : 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                ✕ Reject
              </button>
            </div>
          </div>
        ))}
          </>
        )}

        {/* MARKER_136.W2A: Completed tab content — disk artifacts */}
        {activeTab === 'completed' && (
          <>
            {completedCount === 0 && (
              <div style={{ textAlign: 'center', color: COLORS.textDim, padding: 32, fontSize: 10 }}>
                no completed artifacts<br />
                <span style={{ fontSize: 9, color: COLORS.textDim }}>pipeline outputs appear here</span>
              </div>
            )}

            {panelArtifacts.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 9, color: COLORS.textDim, letterSpacing: 1, textTransform: 'uppercase', marginBottom: 6 }}>
                  scanned outputs (/api/artifacts)
                </div>
                {panelArtifacts.map((artifact) => {
                  const isExpanded = expandedPanelArtifact === artifact.id;
                  const content = panelArtifactContent[artifact.id];
                  return (
                    <div key={artifact.id} style={{
                      marginBottom: 6,
                      background: 'rgba(255,255,255,0.02)',
                      borderRadius: 4,
                      border: `1px solid ${COLORS.border}`,
                      overflow: 'hidden',
                    }}>
                      <div
                        onClick={() => {
                          if (!isExpanded) loadPanelArtifactContent(artifact.id);
                          setExpandedPanelArtifact(isExpanded ? null : artifact.id);
                        }}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          padding: '8px 10px',
                          cursor: 'pointer',
                          borderBottom: isExpanded ? `1px solid ${COLORS.border}` : 'none',
                        }}
                      >
                        <span style={{ color: '#555', fontSize: 10 }}>{isExpanded ? '▼' : '▸'}</span>
                        <span style={{ color: COLORS.text, fontSize: 10, flex: 1 }}>{artifact.name}</span>
                        <span style={{ fontSize: 8, color: COLORS.textDim }}>{artifact.status}</span>
                        <span style={{ fontSize: 8, color: COLORS.textDim }}>
                          {artifact.size_bytes > 1024 ? `${(artifact.size_bytes / 1024).toFixed(1)}kb` : `${artifact.size_bytes}b`}
                        </span>
                      </div>
                      {/* MARKER_141.PANEL_ARTIFACT_CONTENT: Show metadata + content on expand */}
                      {isExpanded && (
                        <div style={{ padding: 8 }}>
                          <div style={{ fontSize: 9, color: COLORS.textMuted, lineHeight: 1.5, marginBottom: 6 }}>
                            <div><strong>path:</strong> {artifact.file_path || '-'}</div>
                            <div><strong>type:</strong> {artifact.artifact_type || '-'}</div>
                            <div><strong>language:</strong> {artifact.language || '-'}</div>
                          </div>
                          {content ? (
                            <>
                              <pre style={{
                                background: '#181818',
                                color: '#d0d0d0',
                                padding: '8px 10px',
                                borderRadius: 3,
                                fontSize: 10,
                                fontFamily: 'monospace',
                                overflow: 'auto',
                                maxHeight: 200,
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-word',
                                margin: 0,
                                border: '1px solid #222',
                              }}>
                                {content.slice(0, 3000)}
                                {content.length > 3000 && '\n... (truncated)'}
                              </pre>
                              <button
                                onClick={() => navigator.clipboard.writeText(content)}
                                style={{
                                  marginTop: 6,
                                  background: '#333',
                                  color: COLORS.textMuted,
                                  border: '1px solid #444',
                                  borderRadius: 2,
                                  fontSize: 9,
                                  padding: '2px 8px',
                                  cursor: 'pointer',
                                }}
                              >
                                copy
                              </button>
                            </>
                          ) : (
                            <div style={{ color: COLORS.textDim, fontSize: 10, textAlign: 'center', padding: 10 }}>
                              loading content...
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {feedbackReports.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 9, color: COLORS.textDim, letterSpacing: 1, textTransform: 'uppercase', marginBottom: 6 }}>
                  feedback reports (data/feedback/reports)
                </div>
                {feedbackReports.map((report) => {
                  const isExpanded = expandedReport === report.run_id;
                  const content = reportContent[report.run_id];
                  return (
                    <div key={report.run_id} style={{
                      marginBottom: 6,
                      background: 'rgba(255,255,255,0.02)',
                      borderRadius: 4,
                      border: `1px solid ${COLORS.border}`,
                      overflow: 'hidden',
                    }}>
                      <div
                        onClick={() => {
                          if (!isExpanded) loadFeedbackReportContent(report.run_id);
                          setExpandedReport(isExpanded ? null : report.run_id);
                        }}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          padding: '8px 10px',
                          cursor: 'pointer',
                          borderBottom: isExpanded ? `1px solid ${COLORS.border}` : 'none',
                        }}
                      >
                        <span style={{ color: '#555', fontSize: 10 }}>{isExpanded ? '▼' : '▸'}</span>
                        <span style={{ color: COLORS.text, fontSize: 10, flex: 1 }}>{report.run_id}</span>
                        <span style={{ fontSize: 8, color: COLORS.textDim }}>{report.status || '-'}</span>
                        <span style={{ fontSize: 8, color: getScoreColor(report.quality_score || 0) }}>
                          {report.quality_score !== undefined ? `${Math.round((report.quality_score || 0) * 100)}%` : '-'}
                        </span>
                      </div>
                      {isExpanded && (
                        <div style={{ padding: 8 }}>
                          <div style={{ fontSize: 9, color: COLORS.textMuted, marginBottom: 6 }}>
                            {report.task || 'No task title'}
                          </div>
                          {content ? (
                            <pre style={{
                              background: '#181818',
                              color: '#d0d0d0',
                              padding: '8px 10px',
                              borderRadius: 3,
                              fontSize: 10,
                              fontFamily: 'monospace',
                              overflow: 'auto',
                              maxHeight: 220,
                              whiteSpace: 'pre-wrap',
                              wordBreak: 'break-word',
                              margin: 0,
                              border: '1px solid #222',
                            }}>
                              {content.slice(0, 3500)}
                              {content.length > 3500 && '\n... (truncated)'}
                            </pre>
                          ) : (
                            <div style={{ color: COLORS.textDim, fontSize: 10 }}>loading...</div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {diskArtifacts.length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 9, color: COLORS.textDim, letterSpacing: 1, textTransform: 'uppercase', marginBottom: 6 }}>
                  disk artifacts (data/artifacts)
                </div>
                {diskArtifacts.map((artifact) => {
                  const isExpanded = expandedDiskArtifact === artifact.filename;
                  const content = diskArtifactContent[artifact.filename];

                  return (
                    <div key={artifact.filename} style={{
                      marginBottom: 8,
                      background: 'rgba(255,255,255,0.02)',
                      borderRadius: 4,
                      border: `1px solid ${COLORS.border}`,
                      overflow: 'hidden',
                    }}>
                      {/* Artifact header */}
                      <div
                        onClick={() => {
                          if (!isExpanded) {
                            loadDiskArtifactContent(artifact.filename);
                          }
                          setExpandedDiskArtifact(isExpanded ? null : artifact.filename);
                        }}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          padding: '8px 10px',
                          cursor: 'pointer',
                          borderBottom: isExpanded ? `1px solid ${COLORS.border}` : 'none',
                        }}
                      >
                        <span style={{ color: '#555', fontSize: 10 }}>
                          {isExpanded ? '▼' : '▸'}
                        </span>
                        <span style={{ color: COLORS.text, fontSize: 10, flex: 1 }}>
                          {artifact.filename}
                        </span>
                        <span style={{
                          fontSize: 8,
                          color: COLORS.textDim,
                          background: 'rgba(255,255,255,0.04)',
                          padding: '1px 4px',
                          borderRadius: 2,
                        }}>
                          {artifact.extension}
                        </span>
                        <span style={{ fontSize: 8, color: COLORS.textDim }}>
                          {artifact.size > 1024 ? `${(artifact.size / 1024).toFixed(1)}kb` : `${artifact.size}b`}
                        </span>
                      </div>

                      {/* Expanded content */}
                      {isExpanded && (
                        <div style={{ padding: 8 }}>
                          {content ? (
                            <>
                              <pre style={{
                                background: '#181818',
                                color: '#d0d0d0',
                                padding: '8px 10px',
                                borderRadius: 3,
                                fontSize: 10,
                                fontFamily: 'monospace',
                                overflow: 'auto',
                                maxHeight: 200,
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-word',
                                margin: 0,
                                border: '1px solid #222',
                              }}>
                                {content.slice(0, 3000)}
                                {content.length > 3000 && '\n... (truncated)'}
                              </pre>
                              <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                                <button
                                  onClick={() => navigator.clipboard.writeText(content)}
                                  style={{
                                    background: '#333',
                                    color: COLORS.textMuted,
                                    border: '1px solid #444',
                                    borderRadius: 2,
                                    fontSize: 9,
                                    padding: '2px 8px',
                                    cursor: 'pointer',
                                  }}
                                >
                                  copy
                                </button>
                                <span style={{ flex: 1 }} />
                                <span style={{ fontSize: 8, color: COLORS.textDim }}>
                                  {new Date(artifact.modified).toLocaleString()}
                                </span>
                              </div>
                            </>
                          ) : (
                            <div style={{ color: COLORS.textDim, fontSize: 10, textAlign: 'center', padding: 10 }}>
                              loading...
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
