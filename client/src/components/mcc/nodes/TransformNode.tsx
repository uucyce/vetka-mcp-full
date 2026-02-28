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
import { resolveMiniScale, scalePx } from './miniScale';

interface TransformNodeProps {
  data: {
    label: string;
    status: NodeStatus;
    mappingCount?: number;
    mini?: boolean;
    miniScale?: number;
  };
  selected?: boolean;
}

function TransformNodeComponent({ data, selected }: TransformNodeProps) {
  const borderColor = getStatusBorderColor(data.status);
  const isRunning = data.status === 'running';
  const isMini = Boolean(data.mini);
  const compactScale = resolveMiniScale(isMini, data.miniScale);

  return (
    <div
      style={{
        background: NOLAN_PALETTE.bgLight,
        border: `1px solid ${borderColor}`,
        borderRadius: isMini ? scalePx(3, compactScale, 2) : 3,
        padding: isMini ? `${scalePx(2, compactScale, 1)}px ${scalePx(6, compactScale, 3)}px` : '6px 12px',
        minWidth: isMini ? scalePx(40, compactScale, 32) : 110,
        fontFamily: 'monospace',
        textAlign: 'center',
        // Subtle trapezoid hint via asymmetric border radius
        borderTopLeftRadius: isMini ? scalePx(8, compactScale, 5) : 8,
        borderTopRightRadius: isMini ? scalePx(8, compactScale, 5) : 8,
        borderBottomLeftRadius: isMini ? scalePx(2, compactScale, 1) : 2,
        borderBottomRightRadius: isMini ? scalePx(2, compactScale, 1) : 2,
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
        <span style={{ fontSize: isMini ? scalePx(8, compactScale, 6) : 11, color: NOLAN_PALETTE.textMuted }}>⟐</span>
        <span
          style={{
            fontSize: isMini ? scalePx(7, compactScale, 6) : 10,
            color: NOLAN_PALETTE.text,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            maxWidth: isMini ? scalePx(28, compactScale, 22) : 90,
          }}
        >
          {data.label}
        </span>
      </div>

      {/* Mapping count */}
      {data.mappingCount !== undefined && (
        <div style={{ fontSize: isMini ? scalePx(6, compactScale, 5) : 8, color: NOLAN_PALETTE.textDim, marginTop: isMini ? scalePx(1, compactScale, 1) : 2 }}>
          {data.mappingCount} mapping{data.mappingCount !== 1 ? 's' : ''}
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
          width: scalePx(5, compactScale, 3),
          height: scalePx(5, compactScale, 3),
        }}
      />
    </div>
  );
}

export const TransformNode = memo(TransformNodeComponent);
