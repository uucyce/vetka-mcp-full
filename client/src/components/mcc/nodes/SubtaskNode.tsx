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
import { resolveMiniScale, scalePx } from './miniScale';

interface SubtaskNodeProps {
  data: {
    label: string;
    status: NodeStatus;
    tokens?: number;
    durationS?: number;
    mini?: boolean;
    miniScale?: number;
  };
  selected?: boolean;
}

function SubtaskNodeComponent({ data, selected }: SubtaskNodeProps) {
  const borderColor = getStatusBorderColor(data.status);
  const isRunning = data.status === 'running';
  const isWorkflowCompact = Boolean(data.mini);
  const compactScale = resolveMiniScale(isWorkflowCompact, data.miniScale);

  return (
    <div
      style={{
        background: NOLAN_PALETTE.bgLight,
        border: `1px solid ${borderColor}`,
        borderRadius: isWorkflowCompact ? scalePx(2, compactScale, 2) : 3,
        padding: isWorkflowCompact ? `${scalePx(2, compactScale, 1)}px ${scalePx(5, compactScale, 3)}px` : '6px 10px',
        minWidth: isWorkflowCompact ? scalePx(42, compactScale, 32) : 120,
        width: isWorkflowCompact ? scalePx(58, compactScale, 42) : undefined,
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
        type="source"
        id="source-top"
        position={Position.Top}
        style={{ opacity: 0, width: 2, height: 2, background: 'transparent', border: 'none' }}
      />
      <Handle
        type="target"
        id="target-top"
        position={Position.Top}
        style={{ background: NOLAN_PALETTE.border, width: scalePx(5, compactScale, 3), height: scalePx(5, compactScale, 3) }}
      />
      <Handle
        type="target"
        id="target-bottom"
        position={Position.Bottom}
        style={{ opacity: 0, width: 2, height: 2, background: 'transparent', border: 'none' }}
      />

      {/* Subtask label */}
      <div
        style={{
          color: NOLAN_PALETTE.text,
          fontSize: isWorkflowCompact ? scalePx(8, compactScale, 7) : 10,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          maxWidth: isWorkflowCompact ? scalePx(56, compactScale, 40) : 120,
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
            marginTop: isWorkflowCompact ? scalePx(1, compactScale, 1) : 3,
            fontSize: isWorkflowCompact ? scalePx(7, compactScale, 6) : 8,
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
        id="source-bottom"
        position={Position.Bottom}
        style={{ background: NOLAN_PALETTE.border, width: scalePx(5, compactScale, 3), height: scalePx(5, compactScale, 3) }}
      />
    </div>
  );
}

export const SubtaskNode = memo(SubtaskNodeComponent);
