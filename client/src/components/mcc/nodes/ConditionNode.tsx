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

interface ConditionNodeProps {
  data: {
    label: string;
    status: NodeStatus;
    expression?: string;
  };
  selected?: boolean;
}

function ConditionNodeComponent({ data, selected }: ConditionNodeProps) {
  const borderColor = getStatusBorderColor(data.status);
  const isRunning = data.status === 'running';

  return (
    <div
      style={{
        width: 80,
        height: 80,
        position: 'relative',
      }}
    >
      {/* Diamond shape — rotated square */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          width: 56,
          height: 56,
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
        <div style={{ fontSize: 14, color: NOLAN_PALETTE.text }}>◇</div>
        <div
          style={{
            fontSize: 9,
            color: NOLAN_PALETTE.textMuted,
            maxWidth: 70,
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
        position={Position.Top}
        style={{
          background: NOLAN_PALETTE.borderLight,
          width: 6,
          height: 6,
          top: 2,
        }}
      />
      {/* True branch — left */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="true"
        style={{
          background: NOLAN_PALETTE.borderLight,
          width: 6,
          height: 6,
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
          width: 6,
          height: 6,
          bottom: 2,
          left: '70%',
        }}
      />
    </div>
  );
}

export const ConditionNode = memo(ConditionNodeComponent);
