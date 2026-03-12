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
    graphKind?: string;
    rd_depth?: number;
    rd_depth_total?: number;
  };
  selected?: boolean;
}

type MiniGenerationPolicy = {
  visualFloor: number;
  edgeFloor: number;
  minWidthFloor: number;
  maxWidthFloor: number;
  handleFloor: number;
  badgeFloor: number;
  labelFontFloor: number;
  metaFontFloor: number;
};

function getMiniGenerationPolicy(depth: number): MiniGenerationPolicy {
  if (depth <= 1) {
    return {
      visualFloor: 0.08,
      edgeFloor: 0.12,
      minWidthFloor: 18,
      maxWidthFloor: 28,
      handleFloor: 1,
      badgeFloor: 4,
      labelFontFloor: 3,
      metaFontFloor: 2,
    };
  }
  if (depth === 2) {
    return {
      visualFloor: 0.04,
      edgeFloor: 0.08,
      minWidthFloor: 10,
      maxWidthFloor: 14,
      handleFloor: 1,
      badgeFloor: 3,
      labelFontFloor: 2,
      metaFontFloor: 1,
    };
  }
  return {
    visualFloor: 0.02,
    edgeFloor: 0.05,
    minWidthFloor: 7,
    maxWidthFloor: 10,
    handleFloor: 1,
    badgeFloor: 2,
    labelFontFloor: 1,
    metaFontFloor: 1,
  };
}

function RoadmapTaskNodeComponent({ data, selected }: RoadmapTaskNodeProps) {
  const borderColor = getStatusBorderColor(data.status);
  const isRunning = data.status === 'running';
  const isDone = data.status === 'done';
  const isSuggested = data.anchorState === 'suggested';
  const isMini = Boolean(data.mini);
  const compactScale = resolveMiniScale(isMini, data.miniScale);
  const fractalDepth = Math.max(0, Number(data.rd_depth_total ?? data.rd_depth ?? 0));
  const generationPolicy = getMiniGenerationPolicy(fractalDepth);
  const fractalScale = Math.max(0.34, 1 / Math.pow(1.6, fractalDepth));
  const visualScale = isMini ? Math.max(generationPolicy.visualFloor, compactScale * fractalScale) : fractalScale;
  const edgeScale = Math.max(generationPolicy.edgeFloor, visualScale);
  const graphKind = String(data.graphKind || '');
  const isCodeScope = graphKind === 'project_dir' || graphKind === 'project_file' || graphKind === 'project_root';
  const codeKindLabel = graphKind === 'project_dir' ? 'DIR' : graphKind === 'project_file' ? 'FILE' : graphKind === 'project_root' ? 'ROOT' : '';
  const badge = TEAM_BADGE[data.preset || ''];
  const semanticBorderColor = isCodeScope ? 'rgba(180,190,205,0.38)' : borderColor;
  const progressPct = data.subtasksTotal
    ? Math.round((data.subtasksDone || 0) / data.subtasksTotal * 100)
    : 0;

  return (
    <div
      style={{
        border: `${scalePx(2, edgeScale, 1)}px solid ${semanticBorderColor}`,
        borderStyle: isCodeScope ? 'solid' : (isSuggested ? 'dashed' : 'solid'),
        borderRadius: isMini ? scalePx(6, visualScale, 1) : scalePx(6, visualScale, 4),
        padding: isMini
          ? `${scalePx(8, visualScale, 1)}px ${scalePx(12, visualScale, 1)}px`
          : `${scalePx(8, visualScale, 4)}px ${scalePx(12, visualScale, 6)}px`,
        minWidth: isMini ? scalePx(160, visualScale, generationPolicy.minWidthFloor) : scalePx(isCodeScope ? 180 : 160, visualScale, 120),
        maxWidth: isMini ? scalePx(200, visualScale, generationPolicy.maxWidthFloor) : scalePx(isCodeScope ? 220 : 200, visualScale, 140),
        fontFamily: 'monospace',
        cursor: 'pointer',
        position: 'relative',
        boxShadow: selected
          ? `0 0 0 2px ${NOLAN_PALETTE.text}`
          : isRunning
            ? `0 0 12px ${NOLAN_PALETTE.statusRunning}30`
            : isDone
              ? `0 0 6px rgba(136,136,136,0.15)`
              : isCodeScope
                ? '0 0 0 1px rgba(255,255,255,0.04)'
                : 'none',
        animation: isRunning ? 'nodePulse 2s ease-in-out infinite' : 'none',
        transition: 'all 0.2s ease',
        opacity: isCodeScope ? 1 : (isSuggested ? 0.58 : 1),
        background: isCodeScope ? 'rgba(255,255,255,0.02)' : NOLAN_PALETTE.bgLight,
      }}
    >
      {/* Target handle */}
      <Handle
        type="target"
        id="target-top"
        position={Position.Top}
        style={{
          background: NOLAN_PALETTE.borderLight,
          width: isMini ? scalePx(8, edgeScale, generationPolicy.handleFloor) : scalePx(8, edgeScale, 4),
          height: isMini ? scalePx(8, edgeScale, generationPolicy.handleFloor) : scalePx(8, edgeScale, 4),
        }}
      />
      <Handle
        type="source"
        id="source-top"
        position={Position.Top}
        style={{ opacity: 0, width: isMini ? scalePx(2, edgeScale, 1) : 2, height: isMini ? scalePx(2, edgeScale, 1) : 2, background: 'transparent', border: 'none' }}
      />

      {/* Header row: label + badges */}
      <div style={{ display: 'flex', alignItems: 'center', gap: isMini ? scalePx(6, visualScale, 1) : 6, marginBottom: isMini ? scalePx(4, visualScale, 1) : 4 }}>
        {isCodeScope && codeKindLabel ? (
          <span
            style={{
              padding: `${scalePx(1, visualScale, 1)}px ${scalePx(5, visualScale, 1)}px`,
              borderRadius: scalePx(4, visualScale, 1),
              border: '1px solid rgba(255,255,255,0.14)',
              color: '#c5cfda',
              fontSize: isMini ? scalePx(8, visualScale, generationPolicy.metaFontFloor) : scalePx(8, visualScale, 6),
              letterSpacing: 0.6,
              flexShrink: 0,
            }}
          >
            {codeKindLabel}
          </span>
        ) : null}

        {/* Team badge */}
        {badge && !isCodeScope && (
          <span
            style={{
              width: isMini ? scalePx(16, visualScale, generationPolicy.badgeFloor) : scalePx(16, visualScale, 10),
              height: isMini ? scalePx(16, visualScale, generationPolicy.badgeFloor) : scalePx(16, visualScale, 10),
              borderRadius: isMini ? scalePx(3, visualScale, 1) : scalePx(3, visualScale, 2),
              background: `${badge.color}22`,
              border: `1px solid ${badge.color}44`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: isMini ? scalePx(8, visualScale, generationPolicy.metaFontFloor) : scalePx(8, visualScale, 6),
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
              width: isMini ? scalePx(16, visualScale, generationPolicy.badgeFloor) : scalePx(16, visualScale, 10),
              height: isMini ? scalePx(16, visualScale, generationPolicy.badgeFloor) : scalePx(16, visualScale, 10),
              borderRadius: isMini ? scalePx(3, visualScale, 1) : scalePx(3, visualScale, 2),
              background: 'rgba(74, 158, 255, 0.15)',
              border: '1px solid rgba(74, 158, 255, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: isMini ? scalePx(9, visualScale, generationPolicy.metaFontFloor) : scalePx(9, visualScale, 6),
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
          data-testid="dag-node-label"
          data-node-label={data.label}
          data-node-task-id={data.taskId || ''}
          style={{
            color: NOLAN_PALETTE.textAccent,
            fontSize: isMini ? scalePx(11, visualScale, generationPolicy.labelFontFloor) : scalePx(isCodeScope ? 12 : 11, visualScale, 9),
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
              fontSize: isMini ? scalePx(8, visualScale, generationPolicy.metaFontFloor) : scalePx(8, visualScale, 6),
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
      <div style={{ display: 'flex', alignItems: 'center', gap: isMini ? scalePx(5, visualScale, 1) : 5, marginBottom: isMini ? scalePx(4, visualScale, 1) : 4 }}>
        <span
          style={{
            width: isMini ? scalePx(5, visualScale, 1) : scalePx(5, visualScale, 3),
            height: isMini ? scalePx(5, visualScale, 1) : scalePx(5, visualScale, 3),
            borderRadius: '50%',
            background: isCodeScope ? 'rgba(180,190,205,0.68)' : borderColor,
            flexShrink: 0,
          }}
        />
        <span
          style={{
            color: isCodeScope && data.status === 'pending' ? '#6f7c8b' : NOLAN_PALETTE.textDim,
            fontSize: isMini ? scalePx(8, visualScale, generationPolicy.metaFontFloor) : scalePx(8, visualScale, 6),
            textTransform: isCodeScope ? 'none' : 'uppercase',
            letterSpacing: isCodeScope ? 0.4 : 1,
          }}
        >
          {isCodeScope ? 'code scope' : data.status}
        </span>

        {/* Subtask counter */}
        {data.subtasksTotal != null && data.subtasksTotal > 0 && (
          <span style={{ color: '#555', fontSize: isMini ? scalePx(8, visualScale, generationPolicy.metaFontFloor) : scalePx(8, visualScale, 6), marginLeft: 'auto' }}>
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
            fontSize: isMini ? scalePx(8, visualScale, generationPolicy.metaFontFloor) : scalePx(8, visualScale, 6),
            marginTop: isMini ? scalePx(4, visualScale, 1) : scalePx(4, visualScale, 2),
            lineHeight: 1.3,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
          title={data.description}
        >
          {isCodeScope ? `inside ${data.description}` : data.description}
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
          fontSize: isMini ? scalePx(7, visualScale, generationPolicy.metaFontFloor) : scalePx(7, visualScale, 5),
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
          width: isMini ? scalePx(8, edgeScale, generationPolicy.handleFloor) : scalePx(8, edgeScale, 4),
          height: isMini ? scalePx(8, edgeScale, generationPolicy.handleFloor) : scalePx(8, edgeScale, 4),
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
