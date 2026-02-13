/**
 * MARKER_144.4D: Transform Node — data mapping between nodes.
 * Trapezoid-ish shape (wider top, narrower bottom via clip-path).
 * Single target + single source handle.
 *
 * @phase 144
 * @status active
 */

import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { NOLAN_PALETTE, getStatusBorderColor } from '../../../utils/dagLayout';
import type { NodeStatus } from '../../../types/dag';

interface TransformNodeProps {
  data: {
    label: string;
    status: NodeStatus;
    mappingCount?: number;
  };
  selected?: boolean;
}

function TransformNodeComponent({ data, selected }: TransformNodeProps) {
  const borderColor = getStatusBorderColor(data.status);
  const isRunning = data.status === 'running';

  return (
    <div
      style={{
        background: NOLAN_PALETTE.bgLight,
        border: `1px solid ${borderColor}`,
        borderRadius: 3,
        padding: '6px 12px',
        minWidth: 110,
        fontFamily: 'monospace',
        textAlign: 'center',
        // Subtle trapezoid hint via asymmetric border radius
        borderTopLeftRadius: 8,
        borderTopRightRadius: 8,
        borderBottomLeftRadius: 2,
        borderBottomRightRadius: 2,
        boxShadow: selected
          ? `0 0 0 2px ${NOLAN_PALETTE.text}`
          : isRunning
            ? `0 0 4px ${borderColor}20`
            : 'none',
        animation: isRunning ? 'nodePulse 2s ease-in-out infinite' : 'none',
      }}
    >
      {/* Icon + label */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}>
        <span style={{ fontSize: 11, color: NOLAN_PALETTE.textMuted }}>⟐</span>
        <span
          style={{
            fontSize: 10,
            color: NOLAN_PALETTE.text,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            maxWidth: 90,
          }}
        >
          {data.label}
        </span>
      </div>

      {/* Mapping count */}
      {data.mappingCount !== undefined && (
        <div style={{ fontSize: 8, color: NOLAN_PALETTE.textDim, marginTop: 2 }}>
          {data.mappingCount} mapping{data.mappingCount !== 1 ? 's' : ''}
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
          width: 5,
          height: 5,
        }}
      />
    </div>
  );
}

export const TransformNode = memo(TransformNodeComponent);
