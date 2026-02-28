/**
 * MARKER_154.6A: RoadmapTaskNode — task node for roadmap level.
 *
 * Enhanced visual compared to generic TaskNode:
 * - Team badge (Bronze/Silver/Gold preset indicator)
 * - Subtask progress bar
 * - Double-click affordance hint
 * - Status-aware border + glow animation for running
 *
 * Used at navLevel='roadmap' in Matryoshka DAG-in-DAG navigation.
 *
 * @phase 154
 * @wave 2
 * @status active
 */

import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { NOLAN_PALETTE, getStatusBorderColor } from '../../../utils/dagLayout';
import type { NodeStatus } from '../../../types/dag';
import { resolveMiniScale, scalePx } from './miniScale';

// MARKER_154.6A: Team preset → badge label + color
const TEAM_BADGE: Record<string, { label: string; color: string }> = {
  dragon_bronze: { label: 'B', color: '#cd7f32' },
  dragon_silver: { label: 'S', color: '#c0c0c0' },
  dragon_gold: { label: 'G', color: '#ffd700' },
};

interface RoadmapTaskNodeProps {
  data: {
    label: string;
    status: NodeStatus;
    taskId: string;
    // Extended fields for roadmap rendering
    preset?: string;
    subtasksDone?: number;
    subtasksTotal?: number;
    description?: string;
    layer?: string;
    anchorState?: 'anchored' | 'suggested' | 'unplaced';
    // MARKER_155.INTEGRATION.CHAT_BADGE: VETKA chat linking
    sourceChatId?: string;
    sourceChatUrl?: string;
    mini?: boolean;
    miniScale?: number;
  };
  selected?: boolean;
}

function RoadmapTaskNodeComponent({ data, selected }: RoadmapTaskNodeProps) {
  const borderColor = getStatusBorderColor(data.status);
  const isRunning = data.status === 'running';
  const isDone = data.status === 'done';
  const isSuggested = data.anchorState === 'suggested';
  const isMini = Boolean(data.mini);
  const compactScale = resolveMiniScale(isMini, data.miniScale);
  const badge = TEAM_BADGE[data.preset || ''];
  const progressPct = data.subtasksTotal
    ? Math.round((data.subtasksDone || 0) / data.subtasksTotal * 100)
    : 0;

  return (
    <div
      style={{
        background: NOLAN_PALETTE.bgLight,
        border: `2px solid ${borderColor}`,
        borderStyle: isSuggested ? 'dashed' : 'solid',
        borderRadius: isMini ? scalePx(6, compactScale, 3) : 6,
        padding: isMini
          ? `${scalePx(8, compactScale, 2)}px ${scalePx(12, compactScale, 3)}px`
          : '8px 12px',
        minWidth: isMini ? scalePx(160, compactScale, 44) : 160,
        maxWidth: isMini ? scalePx(200, compactScale, 58) : 200,
        fontFamily: 'monospace',
        cursor: 'pointer',
        position: 'relative',
        boxShadow: selected
          ? `0 0 0 2px ${NOLAN_PALETTE.text}`
          : isRunning
            ? `0 0 12px ${NOLAN_PALETTE.statusRunning}30`
            : isDone
              ? `0 0 6px rgba(136,136,136,0.15)`
              : 'none',
        animation: isRunning ? 'nodePulse 2s ease-in-out infinite' : 'none',
        transition: 'all 0.2s ease',
        opacity: isSuggested ? 0.58 : 1,
      }}
    >
      {/* Target handle */}
      <Handle
        type="target"
        id="target-top"
        position={Position.Top}
        style={{
          background: NOLAN_PALETTE.borderLight,
          width: isMini ? scalePx(8, compactScale, 3) : 8,
          height: isMini ? scalePx(8, compactScale, 3) : 8,
        }}
      />
      <Handle
        type="source"
        id="source-top"
        position={Position.Top}
        style={{ opacity: 0, width: 2, height: 2, background: 'transparent', border: 'none' }}
      />

      {/* Header row: label + badges */}
      <div style={{ display: 'flex', alignItems: 'center', gap: isMini ? scalePx(6, compactScale, 2) : 6, marginBottom: isMini ? scalePx(4, compactScale, 1) : 4 }}>
        {/* Team badge */}
        {badge && (
          <span
            style={{
              width: isMini ? scalePx(16, compactScale, 8) : 16,
              height: isMini ? scalePx(16, compactScale, 8) : 16,
              borderRadius: isMini ? scalePx(3, compactScale, 2) : 3,
              background: `${badge.color}22`,
              border: `1px solid ${badge.color}44`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: isMini ? scalePx(8, compactScale, 5) : 8,
              fontWeight: 700,
              color: badge.color,
              flexShrink: 0,
            }}
            title={data.preset}
          >
            {badge.label}
          </span>
        )}

        {/* MARKER_155.INTEGRATION.CHAT_BADGE: Chat link */}
        {data.sourceChatId && (
          <span
            onClick={(e) => {
              e.stopPropagation();
              const chatUrl = data.sourceChatUrl || `/chat/${data.sourceChatId}`;
              window.open(chatUrl, '_blank');
            }}
            style={{
              width: isMini ? scalePx(16, compactScale, 8) : 16,
              height: isMini ? scalePx(16, compactScale, 8) : 16,
              borderRadius: isMini ? scalePx(3, compactScale, 2) : 3,
              background: 'rgba(74, 158, 255, 0.15)',
              border: '1px solid rgba(74, 158, 255, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: isMini ? scalePx(9, compactScale, 5) : 9,
              cursor: 'pointer',
              flexShrink: 0,
            }}
            title={`Open linked VETKA chat (${data.sourceChatId.slice(0, 8)})`}
          >
            💬
          </span>
        )}

        {/* Task label */}
        <div
          style={{
            color: NOLAN_PALETTE.textAccent,
            fontSize: isMini ? scalePx(11, compactScale, 6) : 11,
            fontWeight: 600,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            flex: 1,
          }}
          title={data.label}
        >
          {data.label}
        </div>

        {isSuggested && (
          <span
            style={{
              color: '#8b8f96',
              fontSize: isMini ? scalePx(8, compactScale, 5) : 8,
              textTransform: 'uppercase',
              letterSpacing: 0.7,
              border: '1px dashed #3a3f48',
              borderRadius: 3,
              padding: '0 4px',
              flexShrink: 0,
            }}
            title="Suggested anchor. Approve to persist."
          >
            suggested
          </span>
        )}
      </div>

      {/* Status row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: isMini ? scalePx(5, compactScale, 2) : 5, marginBottom: isMini ? scalePx(4, compactScale, 1) : 4 }}>
        <span
          style={{
            width: isMini ? scalePx(5, compactScale, 2) : 5,
            height: isMini ? scalePx(5, compactScale, 2) : 5,
            borderRadius: '50%',
            background: borderColor,
            flexShrink: 0,
          }}
        />
        <span
          style={{
            color: NOLAN_PALETTE.textDim,
            fontSize: isMini ? scalePx(8, compactScale, 5) : 8,
            textTransform: 'uppercase',
            letterSpacing: 1,
          }}
        >
          {data.status}
        </span>

        {/* Subtask counter */}
        {data.subtasksTotal != null && data.subtasksTotal > 0 && (
          <span style={{ color: '#555', fontSize: isMini ? scalePx(8, compactScale, 5) : 8, marginLeft: 'auto' }}>
            {data.subtasksDone || 0}/{data.subtasksTotal}
          </span>
        )}
      </div>

      {/* Progress bar */}
      {data.subtasksTotal != null && data.subtasksTotal > 0 && (
        <div
          style={{
            height: isMini ? 1 : 2,
            background: 'rgba(255,255,255,0.05)',
            borderRadius: isMini ? 0 : 1,
            overflow: 'hidden',
            marginTop: isMini ? 1 : 2,
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${progressPct}%`,
              background: isDone ? NOLAN_PALETTE.statusDone : NOLAN_PALETTE.statusRunning,
              borderRadius: isMini ? 0 : 1,
              transition: 'width 0.3s ease',
            }}
          />
        </div>
      )}

      {/* Description snippet */}
      {data.description && (
        <div
          style={{
            color: '#444',
            fontSize: isMini ? scalePx(8, compactScale, 5) : 8,
            marginTop: isMini ? scalePx(4, compactScale, 1) : 4,
            lineHeight: 1.3,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
          title={data.description}
        >
          {data.description}
        </div>
      )}

      {/* Double-click hint (visible on hover via CSS) */}
      <div
        className="roadmap-node-hint"
        style={{
          position: 'absolute',
          bottom: isMini ? -10 : -16,
          left: '50%',
          transform: 'translateX(-50%)',
          fontSize: isMini ? scalePx(7, compactScale, 4) : 7,
          color: '#444',
          whiteSpace: 'nowrap',
          opacity: 0,
          transition: 'opacity 0.15s',
          pointerEvents: 'none',
        }}
      >
        double-click to enter
      </div>

      {/* Source handle */}
      <Handle
        type="source"
        id="source-bottom"
        position={Position.Bottom}
        style={{
          background: NOLAN_PALETTE.borderLight,
          width: isMini ? scalePx(8, compactScale, 3) : 8,
          height: isMini ? scalePx(8, compactScale, 3) : 8,
        }}
      />
      <Handle
        type="target"
        id="target-bottom"
        position={Position.Bottom}
        style={{ opacity: 0, width: 2, height: 2, background: 'transparent', border: 'none' }}
      />
    </div>
  );
}

export const RoadmapTaskNode = memo(RoadmapTaskNodeComponent);
