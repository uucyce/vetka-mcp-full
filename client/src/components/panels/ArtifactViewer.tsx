/**
 * MARKER_C23C: ArtifactViewer — Pipeline artifact staging and approval.
 * Shows pending artifacts from Dragon pipeline with approve/reject buttons.
 * Style: Nolan monochrome.
 *
 * @status active
 * @phase 131
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

interface ApprovalRequest {
  id: string;
  workflow_id: string;
  artifacts: Artifact[];
  eval_score: number;
  eval_feedback: string;
  status: string;
  created_at: string;
}

const API_BASE = 'http://localhost:5001/api/approvals';

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

  useEffect(() => {
    fetchPending();
    const interval = setInterval(fetchPending, 10000);
    return () => clearInterval(interval);
  }, [fetchPending]);

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
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
        paddingBottom: 10,
        borderBottom: `1px solid ${COLORS.border}`
      }}>
        <div>
          <div style={{ fontSize: 10, fontWeight: 600, color: COLORS.text, letterSpacing: 1.5, textTransform: 'uppercase' }}>
            pending artifacts
          </div>
          <div style={{ color: COLORS.textDim, marginTop: 4, fontSize: 9 }}>
            {pending.length} request{pending.length !== 1 ? 's' : ''} awaiting review
          </div>
        </div>
        <button
          onClick={fetchPending}
          disabled={loading}
          style={{
            padding: '4px 8px',
            background: loading ? 'transparent' : `rgba(255,255,255,0.03)`,
            border: `1px solid ${COLORS.border}`,
            borderRadius: 2,
            color: loading ? COLORS.textDim : COLORS.textMuted,
            fontSize: 9,
            fontFamily: 'monospace',
            cursor: loading ? 'wait' : 'pointer',
          }}
        >
          {loading ? '...' : 'refresh'}
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
      </div>
    </div>
  );
}
