/**
 * MARKER_144.4B: Parallel Node — fork/join concurrent execution.
 * Wide rectangle with dashed border.
 * Multiple source handles for parallel branches.
 *
 * @phase 144
 * @status active
 */

import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { NOLAN_PALETTE, getStatusBorderColor } from '../../../utils/dagLayout';
import type { NodeStatus } from '../../../types/dag';
import { resolveMiniScale, scalePx } from './miniScale';

interface ParallelNodeProps {
  data: {
    label: string;
    status: NodeStatus;
    maxConcurrency?: number;
    mini?: boolean;
    miniScale?: number;
  };
  selected?: boolean;
}

function ParallelNodeComponent({ data, selected }: ParallelNodeProps) {
  const borderColor = getStatusBorderColor(data.status);
  const isRunning = data.status === 'running';
  const isMini = Boolean(data.mini);
  const compactScale = resolveMiniScale(isMini, data.miniScale);

  return (
    <div
      style={{
        background: NOLAN_PALETTE.bgLight,
        border: `${isMini ? 1 : 1.5}px dashed ${borderColor}`,
        borderRadius: isMini ? scalePx(3, compactScale, 2) : 3,
        padding: isMini ? `${scalePx(2, compactScale, 1)}px ${scalePx(5, compactScale, 3)}px` : '6px 14px',
        minWidth: isMini ? scalePx(40, compactScale, 32) : 140,
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
      {/* Icon + label row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
        <span style={{ fontSize: isMini ? scalePx(7, compactScale, 5) : 12, color: NOLAN_PALETTE.textMuted }}>⫸</span>
        <span
          style={{
            fontSize: isMini ? scalePx(6, compactScale, 5) : 10,
            fontWeight: 500,
            color: NOLAN_PALETTE.text,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            maxWidth: isMini ? scalePx(28, compactScale, 22) : 100,
          }}
        >
          {data.label}
        </span>
      </div>

      {/* Concurrency info */}
      {data.maxConcurrency && (
        <div style={{ fontSize: isMini ? scalePx(6, compactScale, 5) : 8, color: NOLAN_PALETTE.textDim, marginTop: isMini ? scalePx(1, compactScale, 1) : 2 }}>
          max: {data.maxConcurrency}
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
      {/* Three source handles for parallel branches */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="branch-0"
        style={{
          background: NOLAN_PALETTE.borderLight,
          width: scalePx(5, compactScale, 3),
          height: scalePx(5, compactScale, 3),
          left: '25%',
        }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="branch-1"
        style={{
          background: NOLAN_PALETTE.borderLight,
          width: scalePx(5, compactScale, 3),
          height: scalePx(5, compactScale, 3),
          left: '50%',
        }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="branch-2"
        style={{
          background: NOLAN_PALETTE.borderLight,
          width: scalePx(5, compactScale, 3),
          height: scalePx(5, compactScale, 3),
          left: '75%',
        }}
      />
    </div>
  );
}

export const ParallelNode = memo(ParallelNodeComponent);
