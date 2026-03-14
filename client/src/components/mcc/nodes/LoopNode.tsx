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
import { resolveMiniScale, scalePx } from './miniScale';

interface LoopNodeProps {
  data: {
    label: string;
    status: NodeStatus;
    maxIterations?: number;
    currentIteration?: number;
    mini?: boolean;
    miniScale?: number;
  };
  selected?: boolean;
}

function LoopNodeComponent({ data, selected }: LoopNodeProps) {
  const borderColor = getStatusBorderColor(data.status);
  const isRunning = data.status === 'running';
  const isMini = Boolean(data.mini);
  const compactScale = resolveMiniScale(isMini, data.miniScale);

  return (
    <div
      style={{
        background: NOLAN_PALETTE.bgLight,
        border: `${isMini ? 1 : 1.5}px solid ${borderColor}`,
        borderRadius: isMini ? scalePx(7, compactScale, 5) : 12,
        padding: isMini ? `${scalePx(3, compactScale, 2)}px ${scalePx(6, compactScale, 3)}px` : '7px 12px',
        minWidth: isMini ? scalePx(38, compactScale, 30) : 100,
        fontFamily: 'monospace',
        textAlign: 'center',
        boxShadow: selected
          ? `0 0 0 ${isMini ? 1 : 2}px ${NOLAN_PALETTE.text}`
          : isRunning
            ? `0 0 6px ${borderColor}30`
            : 'none',
        animation: isRunning ? 'nodePulse 2s ease-in-out infinite' : 'none',
      }}
    >
      {/* Icon + label */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}>
        <span style={{ fontSize: isMini ? scalePx(7, compactScale, 5) : 13, color: NOLAN_PALETTE.textMuted }}>↻</span>
        <span
          style={{
            fontSize: isMini ? scalePx(6, compactScale, 5) : 10,
            fontWeight: 500,
            color: NOLAN_PALETTE.text,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            maxWidth: isMini ? scalePx(26, compactScale, 20) : 80,
          }}
        >
          {data.label}
        </span>
      </div>

      {/* Iteration info */}
      {(data.maxIterations || data.currentIteration) && (
        <div style={{ fontSize: isMini ? scalePx(6, compactScale, 5) : 8, color: NOLAN_PALETTE.textDim, marginTop: isMini ? scalePx(1, compactScale, 1) : 2 }}>
          {data.currentIteration !== undefined
            ? `${data.currentIteration}/${data.maxIterations || '∞'}`
            : `max: ${data.maxIterations}`}
        </div>
      )}

      {/* Handles */}
      <Handle
        type="source"
        id="source-top"
        position={Position.Top}
        style={{ opacity: 0, width: 2, height: 2, background: 'transparent', border: 'none' }}
      />
      <Handle
        type="target"
        id="target-top"
        position={Position.Top}
        style={{
          background: NOLAN_PALETTE.borderLight,
          width: scalePx(6, compactScale, 4),
          height: scalePx(6, compactScale, 4),
        }}
      />
      <Handle
        type="target"
        id="target-bottom"
        position={Position.Bottom}
        style={{ opacity: 0, width: 2, height: 2, background: 'transparent', border: 'none' }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        style={{
          background: NOLAN_PALETTE.borderLight,
          width: scalePx(6, compactScale, 4),
          height: scalePx(6, compactScale, 4),
        }}
      />
      {/* Feedback handle — left side for loop-back edges */}
      <Handle
        type="source"
        position={Position.Left}
        id="feedback"
        style={{
          background: NOLAN_PALETTE.border,
          width: scalePx(5, compactScale, 3),
          height: scalePx(5, compactScale, 3),
        }}
      />
    </div>
  );
}

export const LoopNode = memo(LoopNodeComponent);
