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

interface ParallelNodeProps {
  data: {
    label: string;
    status: NodeStatus;
    maxConcurrency?: number;
  };
  selected?: boolean;
}

function ParallelNodeComponent({ data, selected }: ParallelNodeProps) {
  const borderColor = getStatusBorderColor(data.status);
  const isRunning = data.status === 'running';

  return (
    <div
      style={{
        background: NOLAN_PALETTE.bgLight,
        border: `1.5px dashed ${borderColor}`,
        borderRadius: 3,
        padding: '6px 14px',
        minWidth: 140,
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
      {/* Icon + label row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
        <span style={{ fontSize: 12, color: NOLAN_PALETTE.textMuted }}>⫸</span>
        <span
          style={{
            fontSize: 10,
            fontWeight: 500,
            color: NOLAN_PALETTE.text,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            maxWidth: 100,
          }}
        >
          {data.label}
        </span>
      </div>

      {/* Concurrency info */}
      {data.maxConcurrency && (
        <div style={{ fontSize: 8, color: NOLAN_PALETTE.textDim, marginTop: 2 }}>
          max: {data.maxConcurrency}
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
      {/* Three source handles for parallel branches */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="branch-0"
        style={{
          background: NOLAN_PALETTE.borderLight,
          width: 5,
          height: 5,
          left: '25%',
        }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="branch-1"
        style={{
          background: NOLAN_PALETTE.borderLight,
          width: 5,
          height: 5,
          left: '50%',
        }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="branch-2"
        style={{
          background: NOLAN_PALETTE.borderLight,
          width: 5,
          height: 5,
          left: '75%',
        }}
      />
    </div>
  );
}

export const ParallelNode = memo(ParallelNodeComponent);
