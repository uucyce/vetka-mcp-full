/**
 * MARKER_183.6: VerificationChecklist — user verification gate before merge.
 *
 * Shows when task status = pending_user_approval.
 * Displays: test results, verifier confidence, closure files.
 * Actions: APPROVE (triggers merge), REJECT (back to pending), OVERRIDE (advanced).
 *
 * Nolan palette: pure grayscale, no color except subtle status indicators.
 *
 * @phase 183
 * @task tb_1773605393_25
 * @status active
 */

import { useState, useCallback, useEffect } from 'react';
import { NOLAN_PALETTE } from '../../utils/dagLayout';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TestResult {
  command: string;
  passed: boolean;
  exit_code: number;
  stdout?: string;
  stderr?: string;
}

interface ClosureProof {
  pipeline_success?: boolean;
  verifier_confidence?: number;
  tests?: TestResult[];
  commit_hash?: string;
  manual_override?: boolean;
  manual_override_reason?: string;
}

interface VerificationChecklistProps {
  taskId: string;
  taskTitle: string;
  closureProof?: ClosureProof;
  closureFiles?: string[];
  confidenceThreshold?: number;
  onApprove: (taskId: string) => void;
  onReject: (taskId: string, feedback: string) => void;
  onOverride: (taskId: string, reason: string) => void;
  onClose: () => void;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function CheckItem({ label, passed, detail }: { label: string; passed: boolean; detail?: string }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'flex-start',
      gap: 10,
      padding: '8px 0',
      borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
    }}>
      <span style={{
        fontSize: 16,
        lineHeight: '20px',
        opacity: passed ? 1 : 0.5,
      }}>
        {passed ? '✓' : '✕'}
      </span>
      <div style={{ flex: 1 }}>
        <div style={{
          color: passed ? NOLAN_PALETTE.text : NOLAN_PALETTE.textDim,
          fontSize: 13,
          fontWeight: 500,
        }}>
          {label}
        </div>
        {detail && (
          <div style={{
            color: NOLAN_PALETTE.textDim,
            fontSize: 11,
            marginTop: 2,
            fontFamily: 'monospace',
          }}>
            {detail}
          </div>
        )}
      </div>
    </div>
  );
}

function ConfidenceMeter({ value, threshold }: { value: number; threshold: number }) {
  const passed = value >= threshold;
  const pct = Math.min(100, Math.round(value * 100));

  return (
    <div style={{ padding: '8px 0' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: 12,
        color: NOLAN_PALETTE.textMuted,
        marginBottom: 4,
      }}>
        <span>Verifier Confidence</span>
        <span style={{ color: passed ? NOLAN_PALETTE.text : NOLAN_PALETTE.textDim }}>
          {pct}% {passed ? '≥' : '<'} {Math.round(threshold * 100)}%
        </span>
      </div>
      <div style={{
        height: 4,
        background: NOLAN_PALETTE.borderDim,
        borderRadius: 2,
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%',
          width: `${pct}%`,
          background: passed ? NOLAN_PALETTE.text : NOLAN_PALETTE.textDim,
          borderRadius: 2,
          transition: 'width 0.3s ease',
        }} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export function VerificationChecklist({
  taskId,
  taskTitle,
  closureProof,
  closureFiles = [],
  confidenceThreshold = 0.75,
  onApprove,
  onReject,
  onOverride,
  onClose,
}: VerificationChecklistProps) {
  const [rejectFeedback, setRejectFeedback] = useState('');
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [showOverride, setShowOverride] = useState(false);
  const [overrideReason, setOverrideReason] = useState('');
  const [expandedTest, setExpandedTest] = useState<number | null>(null);

  // Escape to close
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  // Derive verification state
  const proof = closureProof || {};
  const tests = proof.tests || [];
  const confidence = typeof proof.verifier_confidence === 'number' ? proof.verifier_confidence : 0;
  const pipelineSuccess = proof.pipeline_success === true;
  const allTestsPassed = tests.length > 0 && tests.every(t => t.passed);
  const confidencePassed = confidence >= confidenceThreshold;
  // Overall readiness
  const allChecksPass = pipelineSuccess && allTestsPassed && confidencePassed;

  const handleApprove = useCallback(() => {
    onApprove(taskId);
  }, [taskId, onApprove]);

  const handleReject = useCallback(() => {
    if (!rejectFeedback.trim()) return;
    onReject(taskId, rejectFeedback.trim());
    setShowRejectForm(false);
    setRejectFeedback('');
  }, [taskId, rejectFeedback, onReject]);

  const handleOverride = useCallback(() => {
    if (!overrideReason.trim()) return;
    onOverride(taskId, overrideReason.trim());
    setShowOverride(false);
    setOverrideReason('');
  }, [taskId, overrideReason, onOverride]);

  return (
    <div style={{
      position: 'fixed',
      bottom: 64,
      left: '50%',
      transform: 'translateX(-50%)',
      width: 420,
      maxHeight: '70vh',
      overflowY: 'auto',
      background: 'rgba(10, 10, 10, 0.95)',
      backdropFilter: 'blur(20px)',
      border: `1px solid ${NOLAN_PALETTE.border}`,
      borderRadius: 12,
      padding: '16px 20px',
      zIndex: 1000,
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
        paddingBottom: 8,
        borderBottom: `1px solid ${NOLAN_PALETTE.border}`,
      }}>
        <div>
          <div style={{ color: NOLAN_PALETTE.textMuted, fontSize: 11, letterSpacing: 1, textTransform: 'uppercase' }}>
            Verification Gate
          </div>
          <div style={{ color: NOLAN_PALETTE.text, fontSize: 14, fontWeight: 600, marginTop: 2 }}>
            {taskTitle.length > 40 ? taskTitle.slice(0, 40) + '…' : taskTitle}
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: NOLAN_PALETTE.textDim,
            cursor: 'pointer',
            fontSize: 18,
            padding: 4,
          }}
        >
          ✕
        </button>
      </div>

      {/* Pipeline Success */}
      <CheckItem
        label="Pipeline completed successfully"
        passed={pipelineSuccess}
        detail={pipelineSuccess ? undefined : 'Pipeline did not report success'}
      />

      {/* Tests */}
      <div style={{ padding: '8px 0', borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}` }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}>
            <span style={{ fontSize: 16, opacity: allTestsPassed ? 1 : 0.5 }}>
              {allTestsPassed ? '✓' : '✕'}
            </span>
            <span style={{
              color: allTestsPassed ? NOLAN_PALETTE.text : NOLAN_PALETTE.textDim,
              fontSize: 13,
              fontWeight: 500,
            }}>
              Tests: {tests.filter(t => t.passed).length}/{tests.length} passed
            </span>
          </div>
        </div>

        {/* Expandable test details */}
        {tests.map((test, i) => (
          <div key={i} style={{ marginLeft: 26, marginTop: 4 }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                cursor: 'pointer',
                fontSize: 12,
                color: test.passed ? NOLAN_PALETTE.textMuted : NOLAN_PALETTE.text,
              }}
              onClick={() => setExpandedTest(expandedTest === i ? null : i)}
            >
              <span>{test.passed ? '✓' : '✕'}</span>
              <span style={{ fontFamily: 'monospace', fontSize: 11 }}>{test.command}</span>
              <span style={{ color: NOLAN_PALETTE.textDim, fontSize: 10 }}>
                {expandedTest === i ? '▾' : '▸'}
              </span>
            </div>
            {expandedTest === i && (test.stdout || test.stderr) && (
              <pre style={{
                margin: '4px 0 4px 18px',
                padding: 8,
                background: NOLAN_PALETTE.bg,
                border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                borderRadius: 4,
                fontSize: 10,
                color: NOLAN_PALETTE.textMuted,
                maxHeight: 120,
                overflow: 'auto',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              }}>
                {test.stdout || test.stderr}
              </pre>
            )}
          </div>
        ))}

        {tests.length === 0 && (
          <div style={{
            marginLeft: 26,
            fontSize: 11,
            color: NOLAN_PALETTE.textDim,
            fontStyle: 'italic',
            marginTop: 4,
          }}>
            No closure tests defined
          </div>
        )}
      </div>

      {/* Confidence */}
      <ConfidenceMeter value={confidence} threshold={confidenceThreshold} />

      {/* Closure Files */}
      {closureFiles.length > 0 && (
        <div style={{ padding: '8px 0', borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}` }}>
          <div style={{
            color: NOLAN_PALETTE.textMuted,
            fontSize: 12,
            marginBottom: 4,
          }}>
            Files to commit ({closureFiles.length})
          </div>
          {closureFiles.map((f, i) => (
            <div key={i} style={{
              fontFamily: 'monospace',
              fontSize: 11,
              color: NOLAN_PALETTE.textDim,
              padding: '2px 0',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              {f}
            </div>
          ))}
        </div>
      )}

      {/* Action Buttons */}
      <div style={{ marginTop: 12 }}>
        {/* Reject feedback form */}
        {showRejectForm && (
          <div style={{ marginBottom: 10 }}>
            <textarea
              value={rejectFeedback}
              onChange={(e) => setRejectFeedback(e.target.value)}
              placeholder="What needs to change?"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault();
                  handleReject();
                }
              }}
              style={{
                width: '100%',
                minHeight: 60,
                background: NOLAN_PALETTE.bg,
                border: `1px solid ${NOLAN_PALETTE.border}`,
                borderRadius: 6,
                color: NOLAN_PALETTE.text,
                fontSize: 12,
                padding: 8,
                resize: 'vertical',
                outline: 'none',
                fontFamily: 'inherit',
              }}
            />
            <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
              <button onClick={handleReject} style={btnStyle(false)}>
                Submit Feedback
              </button>
              <button onClick={() => setShowRejectForm(false)} style={btnDimStyle}>
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Override form (MARKER_183.7) */}
        {showOverride && (
          <div style={{ marginBottom: 10 }}>
            <div style={{
              color: NOLAN_PALETTE.textMuted,
              fontSize: 11,
              marginBottom: 4,
              letterSpacing: 0.5,
              textTransform: 'uppercase',
            }}>
              Override — explain why checks can be bypassed
            </div>
            <textarea
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
              placeholder="Reason for overriding verification..."
              onKeyDown={(e) => {
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault();
                  handleOverride();
                }
              }}
              style={{
                width: '100%',
                minHeight: 50,
                background: NOLAN_PALETTE.bg,
                border: `1px solid ${NOLAN_PALETTE.border}`,
                borderRadius: 6,
                color: NOLAN_PALETTE.text,
                fontSize: 12,
                padding: 8,
                resize: 'vertical',
                outline: 'none',
                fontFamily: 'inherit',
              }}
            />
            <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
              <button
                onClick={handleOverride}
                disabled={!overrideReason.trim()}
                style={{
                  ...btnStyle(false),
                  opacity: overrideReason.trim() ? 1 : 0.4,
                }}
              >
                Confirm Override
              </button>
              <button onClick={() => setShowOverride(false)} style={btnDimStyle}>
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Main action row */}
        {!showRejectForm && !showOverride && (
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button onClick={handleApprove} style={btnStyle(true)}>
              ✓ Approve & Merge
            </button>
            <button onClick={() => setShowRejectForm(true)} style={btnStyle(false)}>
              ✕ Reject
            </button>
            <div style={{ flex: 1 }} />
            {/* Override toggle — advanced, secondary */}
            {!allChecksPass && (
              <button
                onClick={() => setShowOverride(true)}
                style={{
                  ...btnDimStyle,
                  fontSize: 10,
                  letterSpacing: 0.3,
                }}
              >
                Override…
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Button styles (inline, Nolan palette)
// ---------------------------------------------------------------------------

const btnStyle = (primary: boolean): React.CSSProperties => ({
  padding: '8px 16px',
  border: `1px solid ${primary ? NOLAN_PALETTE.text : NOLAN_PALETTE.border}`,
  borderRadius: 6,
  background: primary ? NOLAN_PALETTE.text : 'transparent',
  color: primary ? NOLAN_PALETTE.bg : NOLAN_PALETTE.text,
  fontSize: 13,
  fontWeight: 500,
  cursor: 'pointer',
  transition: 'all 0.15s ease',
  fontFamily: 'inherit',
});

const btnDimStyle: React.CSSProperties = {
  padding: '6px 12px',
  border: `1px solid ${NOLAN_PALETTE.borderDim}`,
  borderRadius: 6,
  background: 'transparent',
  color: NOLAN_PALETTE.textDim,
  fontSize: 11,
  cursor: 'pointer',
  fontFamily: 'inherit',
};

export default VerificationChecklist;
