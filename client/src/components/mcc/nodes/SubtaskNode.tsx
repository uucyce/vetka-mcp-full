/**
 * MARKER_135.1E: Subtask node — individual work items.
 * Small rectangle with token count.
 *
 * @phase 135.1
 * @status active
 */

import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { NOLAN_PALETTE, getStatusBorderColor } from '../../../utils/dagLayout';
import type { NodeStatus } from '../../../types/dag';

interface SubtaskNodeProps {
  data: {
    label: string;
    status: NodeStatus;
    tokens?: number;
    durationS?: number;
    mini?: boolean;
  };
  selected?: boolean;
}

function SubtaskNodeComponent({ data, selected }: SubtaskNodeProps) {
  const borderColor = getStatusBorderColor(data.status);
  const isRunning = data.status === 'running';
  const isWorkflowCompact = Boolean(data.mini);

  return (
    <div
      style={{
        background: NOLAN_PALETTE.bgLight,
        border: `1px solid ${borderColor}`,
        borderRadius: isWorkflowCompact ? 2 : 3,
        padding: isWorkflowCompact ? '2px 5px' : '6px 10px',
        minWidth: isWorkflowCompact ? 42 : 120,
        fontFamily: 'monospace',
        boxShadow: selected
          ? `0 0 0 2px ${NOLAN_PALETTE.text}`
          : isRunning
            ? `0 0 4px ${NOLAN_PALETTE.statusRunning}20`
            : 'none',
        animation: isRunning ? 'nodePulse 2s ease-in-out infinite' : 'none',
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: NOLAN_PALETTE.border, width: 5, height: 5 }}
      />

      {/* Subtask label */}
      <div
        style={{
          color: NOLAN_PALETTE.text,
          fontSize: isWorkflowCompact ? 8 : 10,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          maxWidth: isWorkflowCompact ? 56 : 120,
        }}
      >
        {data.label}
      </div>

      {/* Tokens & duration */}
      {(data.tokens || data.durationS) && (
        <div
          style={{
            display: 'flex',
            gap: 8,
            marginTop: isWorkflowCompact ? 1 : 3,
            fontSize: isWorkflowCompact ? 7 : 8,
            color: NOLAN_PALETTE.textDim,
          }}
        >
          {data.tokens && (
            <span>
              {data.tokens > 1000 ? `${(data.tokens / 1000).toFixed(1)}k` : data.tokens} tok
            </span>
          )}
          {data.durationS && <span>{data.durationS}s</span>}
        </div>
      )}

      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: NOLAN_PALETTE.border, width: 5, height: 5 }}
      />
    </div>
  );
}

export const SubtaskNode = memo(SubtaskNodeComponent);
