/**
 * MARKER_135.1C: Task node — root of the DAG tree.
 * Rectangle with bold border. Shows task title and status.
 *
 * @phase 135.1
 * @status active
 */

import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { NOLAN_PALETTE, getStatusBorderColor } from '../../../utils/dagLayout';
import type { NodeStatus } from '../../../types/dag';

interface TaskNodeProps {
  data: {
    label: string;
    status: NodeStatus;
    taskId: string;
  };
  selected?: boolean;
}

function TaskNodeComponent({ data, selected }: TaskNodeProps) {
  const borderColor = getStatusBorderColor(data.status);
  const isRunning = data.status === 'running';

  return (
    <div
      style={{
        background: NOLAN_PALETTE.bgLight,
        border: `2px solid ${borderColor}`,
        borderRadius: 4,
        padding: '10px 14px',
        minWidth: 140,
        fontFamily: 'monospace',
        boxShadow: selected
          ? `0 0 0 2px ${NOLAN_PALETTE.text}`
          : isRunning
            ? `0 0 8px ${NOLAN_PALETTE.statusRunning}40`
            : 'none',
        animation: isRunning ? 'nodePulse 2s ease-in-out infinite' : 'none',
      }}
    >
      {/* Target handle (edges come FROM children below) */}
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: NOLAN_PALETTE.borderLight, width: 8, height: 8 }}
      />

      {/* Task label */}
      <div
        style={{
          color: NOLAN_PALETTE.textAccent,
          fontSize: 12,
          fontWeight: 600,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          maxWidth: 130,
        }}
      >
        {data.label}
      </div>

      {/* Status indicator */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          marginTop: 4,
        }}
      >
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: borderColor,
          }}
        />
        <span
          style={{
            color: NOLAN_PALETTE.textNormal,
            fontSize: 9,
            textTransform: 'uppercase',
            letterSpacing: 1,
          }}
        >
          {data.status}
        </span>
      </div>

      {/* Source handle (edges go TO agents above) */}
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: NOLAN_PALETTE.borderLight, width: 8, height: 8 }}
      />
    </div>
  );
}

export const TaskNode = memo(TaskNodeComponent);
