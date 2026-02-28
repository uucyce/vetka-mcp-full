/**
 * MARKER_144.4A: Condition Node — if/else branching.
 * Diamond shape (rotated square), amber-tinted border.
 * Two source handles: true (left-bottom) and false (right-bottom).
 *
 * @phase 144
 * @status active
 */

import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { NOLAN_PALETTE, getStatusBorderColor } from '../../../utils/dagLayout';
import type { NodeStatus } from '../../../types/dag';
import { resolveMiniScale, scalePx } from './miniScale';

interface ConditionNodeProps {
  data: {
    label: string;
    status: NodeStatus;
    expression?: string;
    mini?: boolean;
    miniScale?: number;
  };
  selected?: boolean;
}

function ConditionNodeComponent({ data, selected }: ConditionNodeProps) {
  const borderColor = getStatusBorderColor(data.status);
  const isRunning = data.status === 'running';
  const isMini = Boolean(data.mini);
  const compactScale = resolveMiniScale(isMini, data.miniScale);

  return (
    <div
      style={{
        width: isMini ? scalePx(34, compactScale, 24) : 80,
        height: isMini ? scalePx(34, compactScale, 24) : 80,
        position: 'relative',
      }}
    >
      {/* Diamond shape — rotated square */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          width: isMini ? scalePx(22, compactScale, 16) : 56,
          height: isMini ? scalePx(22, compactScale, 16) : 56,
          transform: 'translate(-50%, -50%) rotate(45deg)',
          background: NOLAN_PALETTE.bgLight,
          border: `2px solid ${borderColor}`,
          borderRadius: 4,
          boxShadow: selected
            ? `0 0 0 2px ${NOLAN_PALETTE.text}`
            : isRunning
              ? `0 0 8px ${borderColor}40`
              : 'none',
          animation: isRunning ? 'nodePulse 2s ease-in-out infinite' : 'none',
        }}
      />

      {/* Content — counter-rotated */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 1,
          textAlign: 'center',
          fontFamily: 'monospace',
          pointerEvents: 'none',
        }}
      >
        <div style={{ fontSize: isMini ? scalePx(8, compactScale, 6) : 14, color: NOLAN_PALETTE.text }}>◇</div>
        <div
          style={{
            fontSize: isMini ? scalePx(6, compactScale, 5) : 9,
            color: NOLAN_PALETTE.textMuted,
            maxWidth: isMini ? scalePx(24, compactScale, 18) : 70,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {data.label}
        </div>
      </div>

      {/* Handles */}
      <Handle
        type="target"
        id="target-top"
        position={Position.Top}
        style={{
          background: NOLAN_PALETTE.borderLight,
          width: scalePx(6, compactScale, 4),
          height: scalePx(6, compactScale, 4),
          top: 2,
        }}
      />
      <Handle
        type="target"
        id="target-bottom"
        position={Position.Bottom}
        style={{ opacity: 0, width: 2, height: 2, background: 'transparent', border: 'none' }}
      />
      {/* True branch — left */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="true"
        style={{
          background: NOLAN_PALETTE.borderLight,
          width: scalePx(6, compactScale, 4),
          height: scalePx(6, compactScale, 4),
          bottom: 2,
          left: '30%',
        }}
      />
      {/* False branch — right */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="false"
        style={{
          background: NOLAN_PALETTE.border,
          width: scalePx(6, compactScale, 4),
          height: scalePx(6, compactScale, 4),
          bottom: 2,
          left: '70%',
        }}
      />
    </div>
  );
}

export const ConditionNode = memo(ConditionNodeComponent);
