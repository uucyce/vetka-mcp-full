/**
 * MARKER_152.10: TaskDAGNode — custom ReactFlow node for Task DAG view.
 * Shows task title, preset, phase_type, status, and mini-stats badge.
 * Read-only node (no editing, no drag-and-drop).
 *
 * @phase 152
 * @status active
 */

import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { NOLAN_PALETTE } from '../../../utils/dagLayout';

interface MiniStats {
  duration_s?: number;
  success?: boolean;
  llm_calls?: number;
  tokens_total?: number;
  cost_estimate?: number;
  subtasks_done?: number;
  subtasks_total?: number;
  retries?: number;
  verifier_confidence?: number;
}

interface TaskDAGNodeData {
  label: string;
  status: string;
  preset?: string;
  phase_type?: string;
  priority?: number;
  color?: string;
  mini_stats?: MiniStats;
  selectedTaskId?: string | null;
  [key: string]: unknown;
}

interface TaskDAGNodeProps {
  id: string;
  data: TaskDAGNodeData;
  selected?: boolean;
}

// Status → icon mapping
function statusIcon(status: string): string {
  switch (status) {
    case 'done': return '\u2705';     // ✅
    case 'failed': return '\u274C';   // ❌
    case 'running': return '\u25CF';  // ●
    case 'hold': return '\u23F8';     // ⏸
    default: return '';
  }
}

// Format duration nicely
function fmtDuration(s: number): string {
  if (s < 60) return `${Math.round(s)}s`;
  const m = Math.floor(s / 60);
  const sec = Math.round(s % 60);
  return sec > 0 ? `${m}m${sec}s` : `${m}m`;
}

function TaskDAGNodeComponent({ id, data, selected }: TaskDAGNodeProps) {
  const {
    label, status, preset, phase_type, color, mini_stats, selectedTaskId,
  } = data;

  const isRunning = status === 'running';
  const isPending = status === 'pending' || status === 'queued';
  const isHold = status === 'hold';
  const isSelected = id === selectedTaskId;

  const borderColor = color || '#555';
  const borderStyle = (isPending || isHold) ? 'dashed' : 'solid';

  return (
    <div
      style={{
        background: NOLAN_PALETTE.bgLight,
        border: `2px ${borderStyle} ${isHold ? '#a98' : borderColor}`,
        borderRadius: 4,
        padding: '8px 10px',
        width: 220,
        fontFamily: 'monospace',
        boxShadow: isSelected
          ? '0 0 0 2px #4ecdc4'
          : selected
            ? `0 0 0 2px ${NOLAN_PALETTE.text}`
            : isRunning
              ? `0 0 8px rgba(255,255,255,0.2)`
              : 'none',
        animation: isRunning ? 'taskDagPulse 2s ease-in-out infinite' : 'none',
        opacity: isPending ? 0.6 : 1,
      }}
    >
      {/* Target handle */}
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: NOLAN_PALETTE.borderLight, width: 6, height: 6 }}
      />

      {/* Row 1: status icon + title */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 5,
      }}>
        {statusIcon(status) && (
          <span style={{ fontSize: 10, lineHeight: 1 }}>{statusIcon(status)}</span>
        )}
        <span style={{
          color: isPending ? '#666' : NOLAN_PALETTE.text,
          fontSize: 11,
          fontWeight: 600,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          flex: 1,
        }}>
          {label?.slice(0, 40) || 'Untitled'}
        </span>
      </div>

      {/* Row 2: preset + phase_type */}
      {(preset || phase_type) && (
        <div style={{
          display: 'flex', gap: 4, marginTop: 3,
          fontSize: 8, color: NOLAN_PALETTE.textDim,
        }}>
          {preset && <span>{preset.replace(/^dragon_/, '').replace(/^titan_/, 't:')}</span>}
          {preset && phase_type && <span style={{ color: '#333' }}>&middot;</span>}
          {phase_type && <span>{phase_type}</span>}
        </div>
      )}

      {/* Row 3: mini-stats badge (only when stats exist) */}
      {mini_stats && (
        <div style={{
          display: 'flex', gap: 8, marginTop: 4,
          fontSize: 8, color: NOLAN_PALETTE.textMuted,
        }}>
          {mini_stats.duration_s != null && (
            <span title="Duration">{'\u23F1'} {fmtDuration(mini_stats.duration_s)}</span>
          )}
          {mini_stats.verifier_confidence != null && (
            <span
              title="Verifier confidence"
              style={{
                color: mini_stats.verifier_confidence >= 0.75 ? '#8a8' : '#a98',
              }}
            >
              {'\u2713'} {Math.round(mini_stats.verifier_confidence * 100)}%
            </span>
          )}
          {(mini_stats.retries ?? 0) > 0 && (
            <span title="Retries">{'\uD83D\uDD01'} {mini_stats.retries}</span>
          )}
        </div>
      )}

      {/* Source handle */}
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: NOLAN_PALETTE.borderLight, width: 6, height: 6 }}
      />
    </div>
  );
}

export const TaskDAGNode = memo(TaskDAGNodeComponent);
