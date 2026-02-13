/**
 * MARKER_144.4E: Group Node — visual container for sub-workflows.
 * Large semi-transparent container, no fill.
 * Children can be placed inside and connect through.
 *
 * @phase 144
 * @status active
 */

import { memo } from 'react';
import { NOLAN_PALETTE } from '../../../utils/dagLayout';
import type { NodeStatus } from '../../../types/dag';

interface GroupNodeProps {
  data: {
    label: string;
    status: NodeStatus;
    collapsed?: boolean;
  };
  selected?: boolean;
}

function GroupNodeComponent({ data, selected }: GroupNodeProps) {
  return (
    <div
      style={{
        background: 'rgba(10, 10, 10, 0.3)',
        border: `1px dashed ${selected ? NOLAN_PALETTE.text : NOLAN_PALETTE.border}`,
        borderRadius: 6,
        minWidth: 220,
        minHeight: 140,
        padding: '4px 8px',
        fontFamily: 'monospace',
        boxShadow: selected
          ? `0 0 0 2px ${NOLAN_PALETTE.text}`
          : 'none',
      }}
    >
      {/* Group header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 5,
          marginBottom: 4,
          borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
          paddingBottom: 3,
        }}
      >
        <span style={{ fontSize: 10, color: NOLAN_PALETTE.textDim }}>⊞</span>
        <span
          style={{
            fontSize: 9,
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
            minHeight: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <span style={{ fontSize: 8, color: NOLAN_PALETTE.textDimmer }}>
            drop nodes here
          </span>
        </div>
      )}
    </div>
  );
}

export const GroupNode = memo(GroupNodeComponent);
