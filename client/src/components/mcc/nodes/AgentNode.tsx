/**
 * MARKER_135.1D: Agent node — pipeline agents (scout, architect, etc).
 * Rounded rectangle with role indicator.
 *
 * @phase 135.1
 * @status active
 */

import { memo, useMemo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { NOLAN_PALETTE, getStatusBorderColor } from '../../../utils/dagLayout';
import type { NodeStatus, AgentRole } from '../../../types/dag';
import { resolveMiniScale, scalePx } from './miniScale';
import { resolveRolePreviewAsset, type MycoRolePreviewRole } from '../mycoRolePreview';

interface AgentNodeProps {
  data: {
    label: string;
    status: NodeStatus;
    role?: AgentRole;
    model?: string;
    durationS?: number;
    mini?: boolean;
    miniScale?: number;
  };
  selected?: boolean;
}

// MARKER_135.5B: Pure grayscale — no colors
function AgentNodeComponent({ data, selected }: AgentNodeProps) {
  const borderColor = getStatusBorderColor(data.status);
  const isRunning = data.status === 'running';
  const isWorkflowCompact = Boolean(data.mini);
  const compactScale = resolveMiniScale(isWorkflowCompact, data.miniScale);
  const isRoadmapDrillMini = isWorkflowCompact && Boolean((data as any).rd_parent);
  const isWorkflowInlineMini = isWorkflowCompact && !isRoadmapDrillMini;

  // MARKER_175.AVATAR: Role avatar badge in DAG nodes
  const roleAvatar = useMemo(() => {
    const role = data.role as MycoRolePreviewRole | undefined;
    if (!role) return null;
    return resolveRolePreviewAsset(role, data.label || role);
  }, [data.role, data.label]);

  return (
    <div
      style={{
        background: NOLAN_PALETTE.bgLight,
        border: `${isWorkflowCompact ? 1 : 1.5}px solid ${borderColor}`,
        borderRadius: isWorkflowCompact ? scalePx(4, compactScale, 2) : 8,
        padding: isWorkflowCompact ? `${scalePx(2, compactScale, 1)}px ${scalePx(5, compactScale, 2)}px` : '8px 12px',
        minWidth: isWorkflowCompact ? scalePx(44, compactScale, 34) : 100,
        width: isWorkflowCompact ? scalePx(58, compactScale, 42) : undefined,
        fontFamily: 'monospace',
        boxShadow: selected
          ? `0 0 0 ${isWorkflowCompact ? 1 : 2}px ${NOLAN_PALETTE.text}`
          : isRunning
            ? `0 0 6px ${NOLAN_PALETTE.statusRunning}30`
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
        style={{ background: NOLAN_PALETTE.borderLight, width: scalePx(6, compactScale, 4), height: scalePx(6, compactScale, 4) }}
      />
      <Handle
        type="target"
        id="target-bottom"
        position={Position.Bottom}
        style={{ opacity: 0, width: 2, height: 2, background: 'transparent', border: 'none' }}
      />

      {/* Role badge — MARKER_175.AVATAR */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: isWorkflowCompact ? scalePx(3, compactScale, 2) : 5,
        }}
      >
        {roleAvatar && !isWorkflowInlineMini ? (
          <img
            src={roleAvatar}
            alt={data.role || 'agent'}
            style={{
              width: isWorkflowCompact ? scalePx(14, compactScale, 10) : 20,
              height: isWorkflowCompact ? scalePx(14, compactScale, 10) : 20,
              borderRadius: isWorkflowCompact ? 2 : 3,
              objectFit: 'cover',
              opacity: isRunning ? 1 : 0.75,
              flexShrink: 0,
            }}
          />
        ) : (
          <span
            style={{
              width: isWorkflowCompact ? scalePx(4, compactScale, 3) : 8,
              height: isWorkflowCompact ? scalePx(4, compactScale, 3) : 8,
              borderRadius: 2,
              background: isRunning ? NOLAN_PALETTE.text : NOLAN_PALETTE.borderLight,
              flexShrink: 0,
            }}
          />
        )}
        <span
          style={{
            color: NOLAN_PALETTE.text,
            fontSize: isWorkflowInlineMini ? scalePx(6, compactScale, 5) : isWorkflowCompact ? scalePx(7, compactScale, 6) : 11,
            fontWeight: 500,
            display: 'inline-block',
            maxWidth: isWorkflowInlineMini ? scalePx(70, compactScale, 44) : isWorkflowCompact ? scalePx(52, compactScale, 32) : 220,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
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
            marginTop: isWorkflowCompact ? scalePx(2, compactScale, 1) : 4,
            fontSize: isWorkflowCompact ? scalePx(7, compactScale, 6) : 9,
            color: NOLAN_PALETTE.textDim,
          }}
        >
          {data.model && <span>{data.model.split('-')[0]}</span>}
          {data.durationS && <span>{data.durationS}s</span>}
        </div>
      )}

      <Handle
        type="source"
        id="source-bottom"
        position={Position.Bottom}
        style={{ background: NOLAN_PALETTE.borderLight, width: scalePx(6, compactScale, 4), height: scalePx(6, compactScale, 4) }}
      />
    </div>
  );
}

export const AgentNode = memo(AgentNodeComponent);
