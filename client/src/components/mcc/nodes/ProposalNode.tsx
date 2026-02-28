/**
 * MARKER_135.1F: Proposal node — diamond shape with confidence glow.
 * Represents pipeline results ready for review.
 *
 * @phase 135.1
 * @status active
 */

import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { NOLAN_PALETTE, getStatusBorderColor, getConfidenceColor } from '../../../utils/dagLayout';
import type { NodeStatus } from '../../../types/dag';
import { resolveMiniScale, scalePx } from './miniScale';

interface ProposalNodeProps {
  data: {
    label: string;
    status: NodeStatus;
    confidence?: number;
    mini?: boolean;
    miniScale?: number;
  };
  selected?: boolean;
}

function ProposalNodeComponent({ data, selected }: ProposalNodeProps) {
  const borderColor = getStatusBorderColor(data.status);
  const confidenceColor = data.confidence ? getConfidenceColor(data.confidence) : NOLAN_PALETTE.borderLight;
  const isReady = data.status === 'done' && data.confidence;
  const isWorkflowCompact = Boolean(data.mini);
  const compactScale = resolveMiniScale(isWorkflowCompact, data.miniScale);

  return (
    <div
      style={{
        position: 'relative',
        width: isWorkflowCompact ? scalePx(40, compactScale, 30) : 100,
        height: isWorkflowCompact ? scalePx(26, compactScale, 20) : 60,
      }}
    >
      <Handle
        type="target"
        id="target-top"
        position={Position.Top}
        style={{
          background: NOLAN_PALETTE.borderLight,
          width: scalePx(6, compactScale, 4),
          height: scalePx(6, compactScale, 4),
          top: 0,
          left: '50%',
          transform: 'translateX(-50%)',
        }}
      />
      <Handle
        type="target"
        id="target-bottom"
        position={Position.Bottom}
        style={{
          opacity: 0,
          width: 2,
          height: 2,
          background: 'transparent',
          border: 'none',
          bottom: 0,
          left: '50%',
          transform: 'translateX(-50%)',
        }}
      />

      {/* Diamond shape */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          width: isWorkflowCompact ? scalePx(30, compactScale, 22) : 80,
          height: isWorkflowCompact ? scalePx(20, compactScale, 16) : 50,
          transform: 'translate(-50%, -50%) rotate(45deg)',
          background: NOLAN_PALETTE.bgLight,
          border: `2px solid ${borderColor}`,
          borderRadius: 4,
          boxShadow: selected
            ? `0 0 0 2px ${NOLAN_PALETTE.text}`
            : isReady
              ? `0 0 12px ${confidenceColor}60`
              : 'none',
        }}
      />

      {/* Content (counter-rotated) */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          textAlign: 'center',
          fontFamily: 'monospace',
          zIndex: 1,
        }}
      >
        {/* Confidence indicator */}
        {data.confidence !== undefined && (
          <div
            style={{
              fontSize: isWorkflowCompact ? scalePx(9, compactScale, 7) : 14,
              fontWeight: 600,
              color: confidenceColor,
            }}
          >
            {Math.round(data.confidence * 100)}%
          </div>
        )}

        {/* Label */}
        <div
          style={{
            fontSize: isWorkflowCompact ? scalePx(6, compactScale, 5) : 8,
            color: NOLAN_PALETTE.textNormal,
            textTransform: 'uppercase',
            letterSpacing: 0.5,
            marginTop: 2,
          }}
        >
          proposal
        </div>
      </div>

      {/* No source handle — proposals are terminal nodes */}
    </div>
  );
}

export const ProposalNode = memo(ProposalNodeComponent);
