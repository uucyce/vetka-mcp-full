/**
 * MARKER_135.1D: Agent node — pipeline agents (scout, architect, etc).
 * Rounded rectangle with role indicator.
 *
 * @phase 135.1
 * @status active
 */

import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { NOLAN_PALETTE, getStatusBorderColor } from '../../../utils/dagLayout';
import type { NodeStatus, AgentRole } from '../../../types/dag';

interface AgentNodeProps {
  data: {
    label: string;
    status: NodeStatus;
    role?: AgentRole;
    model?: string;
    durationS?: number;
  };
  selected?: boolean;
}

// Role colors (subtle, within Nolan palette)
const ROLE_COLORS: Record<AgentRole, string> = {
  scout: '#5a6a5a',
  architect: '#6a6a5a',
  researcher: '#5a5a6a',
  coder: '#5a6a6a',
  verifier: '#6a5a6a',
};

function AgentNodeComponent({ data, selected }: AgentNodeProps) {
  const borderColor = getStatusBorderColor(data.status);
  const isRunning = data.status === 'running';
  const roleColor = data.role ? ROLE_COLORS[data.role] : NOLAN_PALETTE.borderNormal;

  return (
    <div
      style={{
        background: NOLAN_PALETTE.bgNode,
        border: `1.5px solid ${borderColor}`,
        borderRadius: 8,
        padding: '8px 12px',
        minWidth: 100,
        fontFamily: 'monospace',
        boxShadow: selected
          ? `0 0 0 2px ${NOLAN_PALETTE.borderAccent}`
          : isRunning
            ? `0 0 6px ${NOLAN_PALETTE.statusRunning}30`
            : 'none',
        animation: isRunning ? 'nodePulse 2s ease-in-out infinite' : 'none',
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: NOLAN_PALETTE.borderNormal, width: 6, height: 6 }}
      />

      {/* Role badge */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
        }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: 2,
            background: roleColor,
          }}
        />
        <span
          style={{
            color: NOLAN_PALETTE.textBright,
            fontSize: 11,
            fontWeight: 500,
          }}
        >
          {data.label}
        </span>
      </div>

      {/* Model & duration */}
      {(data.model || data.durationS) && (
        <div
          style={{
            display: 'flex',
            gap: 8,
            marginTop: 4,
            fontSize: 9,
            color: NOLAN_PALETTE.textDim,
          }}
        >
          {data.model && <span>{data.model.split('-')[0]}</span>}
          {data.durationS && <span>{data.durationS}s</span>}
        </div>
      )}

      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: NOLAN_PALETTE.borderNormal, width: 6, height: 6 }}
      />
    </div>
  );
}

export const AgentNode = memo(AgentNodeComponent);
