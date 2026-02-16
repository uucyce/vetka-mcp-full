/**
 * MARKER_153.7D: CaptainBar — Architect recommendation banner.
 *
 * Shows at top of MCC center column: "🎯 Next: [task]. [reason]. [Accept] [Skip]"
 * Compact inline bar, not a modal. Dismissible.
 *
 * @phase 153
 * @wave 7
 * @status active
 */

import { useCallback } from 'react';
import { useMCCStore } from '../../store/useMCCStore';
import { NOLAN_PALETTE } from '../../utils/dagLayout';
import type { Recommendation, ProjectProgress } from '../../hooks/useCaptain';

interface CaptainBarProps {
  recommendation: Recommendation | null;
  progress: ProjectProgress | null;
  loading: boolean;
  onAccept: () => void;
  onReject: () => void;
  onDismiss: () => void;
}

export function CaptainBar({
  recommendation,
  progress,
  loading,
  onAccept,
  onReject,
  onDismiss,
}: CaptainBarProps) {
  const navLevel = useMCCStore(s => s.navLevel);

  // Only show at roadmap level
  if (navLevel !== 'roadmap') return null;

  // Loading state
  if (loading) {
    return (
      <div style={barStyle}>
        <span style={{ color: NOLAN_PALETTE.textDim, fontSize: 9 }}>
          🧠 Captain analyzing project...
        </span>
      </div>
    );
  }

  // No recommendation
  if (!recommendation || !recommendation.has_recommendation) {
    if (progress && progress.completed === progress.total && progress.total > 0) {
      return (
        <div style={barStyle}>
          <span style={{ color: '#4ecdc4', fontSize: 9 }}>
            ✓ All {progress.total} modules complete
          </span>
        </div>
      );
    }
    return null;
  }

  return (
    <div style={barStyle}>
      {/* Progress indicator */}
      {progress && (
        <span style={{
          fontSize: 8,
          color: NOLAN_PALETTE.textDim,
          marginRight: 8,
          flexShrink: 0,
        }}>
          {progress.completed}/{progress.total}
        </span>
      )}

      {/* Recommendation */}
      <span style={{
        fontSize: 9,
        color: '#c6ffff',
        fontWeight: 600,
        marginRight: 4,
        flexShrink: 0,
      }}>
        🎯
      </span>
      <span style={{
        fontSize: 9,
        color: NOLAN_PALETTE.text,
        flex: 1,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}>
        {recommendation.module_label}
      </span>

      {/* Confidence badge */}
      <span style={{
        fontSize: 7,
        color: NOLAN_PALETTE.textDim,
        padding: '1px 4px',
        background: 'rgba(255,255,255,0.05)',
        borderRadius: 2,
        marginRight: 6,
        flexShrink: 0,
      }}>
        {recommendation.preset.replace('dragon_', '').charAt(0).toUpperCase()}
        {recommendation.preset.replace('dragon_', '').slice(1)}
      </span>

      {/* Accept button */}
      <button
        onClick={onAccept}
        style={{
          background: 'rgba(78,205,196,0.15)',
          border: '1px solid rgba(78,205,196,0.4)',
          borderRadius: 2,
          color: '#c6ffff',
          fontSize: 8,
          padding: '2px 8px',
          cursor: 'pointer',
          fontFamily: 'monospace',
          fontWeight: 600,
          flexShrink: 0,
        }}
      >
        Accept
      </button>

      {/* Skip/reject */}
      <button
        onClick={onReject}
        style={{
          background: 'transparent',
          border: `1px solid ${NOLAN_PALETTE.borderDim}`,
          borderRadius: 2,
          color: NOLAN_PALETTE.textMuted,
          fontSize: 8,
          padding: '2px 6px',
          cursor: 'pointer',
          fontFamily: 'monospace',
          marginLeft: 4,
          flexShrink: 0,
        }}
      >
        Skip
      </button>

      {/* Dismiss X */}
      <button
        onClick={onDismiss}
        style={{
          background: 'transparent',
          border: 'none',
          color: NOLAN_PALETTE.textDim,
          fontSize: 8,
          padding: '0 2px',
          cursor: 'pointer',
          marginLeft: 4,
          opacity: 0.5,
          flexShrink: 0,
        }}
        title="Dismiss"
      >
        ×
      </button>
    </div>
  );
}

const barStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 4,
  padding: '4px 10px',
  background: 'rgba(0,0,0,0.5)',
  borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
  fontFamily: 'monospace',
  flexShrink: 0,
  minHeight: 24,
};
