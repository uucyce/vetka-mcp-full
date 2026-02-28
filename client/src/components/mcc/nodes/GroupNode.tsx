/**
 * MARKER_144.4E: Group Node — visual container for sub-workflows.
 * Large semi-transparent container, no fill.
 * Children can be placed inside and connect through.
 *
 * @phase 144
 * @status active
 */

import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { NOLAN_PALETTE } from '../../../utils/dagLayout';
import type { NodeStatus } from '../../../types/dag';
import { resolveMiniScale, scalePx } from './miniScale';

interface GroupNodeProps {
  data: {
    label: string;
    status: NodeStatus;
    collapsed?: boolean;
    mini?: boolean;
    miniScale?: number;
  };
  selected?: boolean;
}

function GroupNodeComponent({ data, selected }: GroupNodeProps) {
  const isMini = Boolean(data.mini);
  const compactScale = resolveMiniScale(isMini, data.miniScale);
  return (
    <div
      style={{
        background: 'rgba(10, 10, 10, 0.3)',
        border: `1px dashed ${selected ? NOLAN_PALETTE.text : NOLAN_PALETTE.border}`,
        borderRadius: isMini ? scalePx(6, compactScale, 4) : 6,
        minWidth: isMini ? scalePx(70, compactScale, 52) : 220,
        minHeight: isMini ? scalePx(42, compactScale, 30) : 140,
        padding: isMini ? `${scalePx(2, compactScale, 1)}px ${scalePx(4, compactScale, 2)}px` : '4px 8px',
        fontFamily: 'monospace',
        boxShadow: selected
          ? `0 0 0 2px ${NOLAN_PALETTE.text}`
          : 'none',
      }}
    >
      <Handle
        type="target"
        id="target-top"
        position={Position.Top}
        style={{ background: NOLAN_PALETTE.borderLight, width: 6, height: 6 }}
      />
      <Handle
        type="target"
        id="target-bottom"
        position={Position.Bottom}
        style={{ opacity: 0, width: 2, height: 2, background: 'transparent', border: 'none' }}
      />
      <Handle
        type="source"
        id="source-bottom"
        position={Position.Bottom}
        style={{ background: NOLAN_PALETTE.borderLight, width: 6, height: 6 }}
      />

      {/* Group header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 5,
          marginBottom: isMini ? scalePx(2, compactScale, 1) : 4,
          borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
          paddingBottom: isMini ? scalePx(1, compactScale, 1) : 3,
        }}
      >
        <span style={{ fontSize: isMini ? scalePx(7, compactScale, 6) : 10, color: NOLAN_PALETTE.textDim }}>⊞</span>
        <span
          style={{
            fontSize: isMini ? scalePx(7, compactScale, 6) : 9,
            fontWeight: 500,
            color: NOLAN_PALETTE.textMuted,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
          }}
        >
          {data.label}
        </span>
      </div>

      {/* Placeholder content area — child nodes render here via xyflow parentId */}
      {!data.collapsed && (
        <div
          style={{
            minHeight: isMini ? scalePx(22, compactScale, 16) : 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <span style={{ fontSize: isMini ? scalePx(6, compactScale, 5) : 8, color: NOLAN_PALETTE.textDimmer }}>
            drop nodes here
          </span>
        </div>
      )}
    </div>
  );
}

export const GroupNode = memo(GroupNodeComponent);
