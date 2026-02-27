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
    mini?: boolean;
  };
  selected?: boolean;
}

// MARKER_135.5B: Pure grayscale — no colors
function AgentNodeComponent({ data, selected }: AgentNodeProps) {
  const borderColor = getStatusBorderColor(data.status);
  const isRunning = data.status === 'running';
  const isWorkflowCompact = Boolean(data.mini);

  return (
    <div
      style={{
        background: NOLAN_PALETTE.bgLight,
        border: `1.5px solid ${borderColor}`,
        borderRadius: isWorkflowCompact ? 5 : 8,
        padding: isWorkflowCompact ? '3px 6px' : '8px 12px',
        minWidth: isWorkflowCompact ? 44 : 100,
        fontFamily: 'monospace',
        boxShadow: selected
          ? `0 0 0 2px ${NOLAN_PALETTE.text}`
          : isRunning
            ? `0 0 6px ${NOLAN_PALETTE.statusRunning}30`
            : 'none',
        animation: isRunning ? 'nodePulse 2s ease-in-out infinite' : 'none',
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: NOLAN_PALETTE.borderLight, width: 6, height: 6 }}
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
            width: isWorkflowCompact ? 4 : 8,
            height: isWorkflowCompact ? 4 : 8,
            borderRadius: 2,
            background: isRunning ? NOLAN_PALETTE.text : NOLAN_PALETTE.borderLight,
          }}
        />
        <span
          style={{
            color: NOLAN_PALETTE.text,
            fontSize: isWorkflowCompact ? 8 : 11,
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
            marginTop: isWorkflowCompact ? 2 : 4,
            fontSize: isWorkflowCompact ? 7 : 9,
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
        style={{ background: NOLAN_PALETTE.borderLight, width: 6, height: 6 }}
      />
    </div>
  );
}

export const AgentNode = memo(AgentNodeComponent);
