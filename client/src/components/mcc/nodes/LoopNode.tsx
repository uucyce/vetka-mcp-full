/**
 * MARKER_144.4C: Loop Node — repeat with exit condition.
 * Rounded rectangle with cycle arrow icon.
 * Has feedback handle on left side for loop-back edges.
 *
 * @phase 144
 * @status active
 */

import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { NOLAN_PALETTE, getStatusBorderColor } from '../../../utils/dagLayout';
import type { NodeStatus } from '../../../types/dag';

interface LoopNodeProps {
  data: {
    label: string;
    status: NodeStatus;
    maxIterations?: number;
    currentIteration?: number;
  };
  selected?: boolean;
}

function LoopNodeComponent({ data, selected }: LoopNodeProps) {
  const borderColor = getStatusBorderColor(data.status);
  const isRunning = data.status === 'running';

  return (
    <div
      style={{
        background: NOLAN_PALETTE.bgLight,
        border: `1.5px solid ${borderColor}`,
        borderRadius: 12,
        padding: '7px 12px',
        minWidth: 100,
        fontFamily: 'monospace',
        textAlign: 'center',
        boxShadow: selected
          ? `0 0 0 2px ${NOLAN_PALETTE.text}`
          : isRunning
            ? `0 0 6px ${borderColor}30`
            : 'none',
        animation: isRunning ? 'nodePulse 2s ease-in-out infinite' : 'none',
      }}
    >
      {/* Icon + label */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}>
        <span style={{ fontSize: 13, color: NOLAN_PALETTE.textMuted }}>↻</span>
        <span
          style={{
            fontSize: 10,
            fontWeight: 500,
            color: NOLAN_PALETTE.text,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            maxWidth: 80,
          }}
        >
          {data.label}
        </span>
      </div>

      {/* Iteration info */}
      {(data.maxIterations || data.currentIteration) && (
        <div style={{ fontSize: 8, color: NOLAN_PALETTE.textDim, marginTop: 2 }}>
          {data.currentIteration !== undefined
            ? `${data.currentIteration}/${data.maxIterations || '∞'}`
            : `max: ${data.maxIterations}`}
        </div>
      )}

      {/* Handles */}
      <Handle
        type="target"
        position={Position.Top}
        style={{
          background: NOLAN_PALETTE.borderLight,
          width: 6,
          height: 6,
        }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        style={{
          background: NOLAN_PALETTE.borderLight,
          width: 6,
          height: 6,
        }}
      />
      {/* Feedback handle — left side for loop-back edges */}
      <Handle
        type="source"
        position={Position.Left}
        id="feedback"
        style={{
          background: NOLAN_PALETTE.border,
          width: 5,
          height: 5,
        }}
      />
    </div>
  );
}

export const LoopNode = memo(LoopNodeComponent);
