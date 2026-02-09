/**
 * MARKER_126.2A: TaskCard — Nolan dark style, no emoji.
 * CSS-only status indicators, monochrome priority, glassmorphism accents.
 * Phase 126.2: Style upgrade — "Batman Nolan, not Burton"
 *
 * @status active
 * @phase 126.2
 * @depends react
 * @used_by DevPanel
 */

import { useState } from 'react';

export interface TaskData {
  id: string;
  title: string;
  description?: string;
  priority: number;
  status: string;
  phase_type: string;
  preset?: string;
  tags?: string[];
  source?: string;
  created_at?: string;
}

interface TaskCardProps {
  task: TaskData;
  onPriorityChange?: (taskId: string, priority: number) => void;
  onRemove?: (taskId: string) => void;
  onDispatch?: (taskId: string) => void;
}

// Priority: monochrome gradient, P1=brightest, P5=dimmest
const PRIORITY_STYLE: Record<number, { bg: string; border: string; text: string }> = {
  1: { bg: '#e0e0e0', border: '#fff', text: '#000' },
  2: { bg: '#aaa', border: '#ccc', text: '#111' },
  3: { bg: '#666', border: '#888', text: '#eee' },
  4: { bg: '#444', border: '#666', text: '#ccc' },
  5: { bg: '#2a2a2a', border: '#444', text: '#888' },
};

// Status: CSS indicators instead of emoji
// dot = small circle, pulse = animated ring, bar = horizontal line
type StatusShape = 'dot' | 'pulse' | 'ring' | 'bar' | 'x';

interface StatusDef {
  shape: StatusShape;
  color: string;
  glow?: string;
  label: string;
}

const STATUS_DEF: Record<string, StatusDef> = {
  pending:   { shape: 'dot',   color: '#555',    label: 'pending' },
  queued:    { shape: 'dot',   color: '#888',    label: 'queued' },
  running:   { shape: 'pulse', color: '#e0e0e0', glow: 'rgba(224,224,224,0.3)', label: 'running' },
  done:      { shape: 'ring',  color: '#8a8',    label: 'done' },
  failed:    { shape: 'x',     color: '#a66',    label: 'failed' },
  cancelled: { shape: 'bar',   color: '#555',    label: 'cancelled' },
  hold:      { shape: 'bar',   color: '#a98',    label: 'hold' },
};

// Phase type: minimal monochrome symbols (no emoji)
const PHASE_SYMBOL: Record<string, string> = {
  build: '▸',
  fix: '×',
  research: '◎',
};

// ── CSS Status Indicator ──
function StatusIndicator({ status }: { status: string }) {
  const def = STATUS_DEF[status] || STATUS_DEF.pending;
  const size = 8;

  if (def.shape === 'pulse') {
    return (
      <span style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: size + 8, height: size + 8 }}>
        {/* Pulsing outer ring */}
        <span style={{
          position: 'absolute',
          width: size + 6,
          height: size + 6,
          borderRadius: '50%',
          border: `1px solid ${def.color}`,
          opacity: 0.4,
          animation: 'taskPulse 1.5s ease-in-out infinite',
        }} />
        {/* Solid inner dot */}
        <span style={{
          width: size,
          height: size,
          borderRadius: '50%',
          background: def.color,
          boxShadow: def.glow ? `0 0 6px ${def.glow}` : 'none',
        }} />
      </span>
    );
  }

  if (def.shape === 'ring') {
    return (
      <span style={{
        display: 'inline-block',
        width: size,
        height: size,
        borderRadius: '50%',
        border: `2px solid ${def.color}`,
        background: 'transparent',
      }} />
    );
  }

  if (def.shape === 'x') {
    return (
      <span style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: size + 2,
        height: size + 2,
        color: def.color,
        fontSize: 10,
        fontWeight: 700,
        fontFamily: 'monospace',
        lineHeight: 1,
      }}>✕</span>
    );
  }

  if (def.shape === 'bar') {
    return (
      <span style={{
        display: 'inline-block',
        width: 10,
        height: 2,
        background: def.color,
        borderRadius: 1,
        marginTop: 1,
      }} />
    );
  }

  // Default: dot
  return (
    <span style={{
      display: 'inline-block',
      width: size,
      height: size,
      borderRadius: '50%',
      background: def.color,
    }} />
  );
}

// ── Inject keyframe animation (once) ──
let _injected = false;
function injectKeyframes() {
  if (_injected || typeof document === 'undefined') return;
  const style = document.createElement('style');
  style.textContent = `
    @keyframes taskPulse {
      0%, 100% { transform: scale(1); opacity: 0.4; }
      50% { transform: scale(1.4); opacity: 0.1; }
    }
  `;
  document.head.appendChild(style);
  _injected = true;
}

// ── TaskCard ──
export function TaskCard({ task, onPriorityChange, onRemove, onDispatch }: TaskCardProps) {
  injectKeyframes();
  const [expanded, setExpanded] = useState(false);
  const [hover, setHover] = useState(false);

  const prio = PRIORITY_STYLE[task.priority] || PRIORITY_STYLE[5];
  const phaseSymbol = PHASE_SYMBOL[task.phase_type] || '·';
  const isDispatchable = task.status === 'pending' || task.status === 'queued';

  return (
    <div
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        padding: '8px 10px',
        marginBottom: 4,
        background: hover
          ? 'rgba(255,255,255,0.04)'
          : expanded
            ? 'rgba(255,255,255,0.03)'
            : 'rgba(255,255,255,0.015)',
        borderRadius: 4,
        borderLeft: `2px solid ${prio.bg}`,
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        backdropFilter: hover ? 'blur(2px)' : 'none',
      }}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Top row: priority + phase + title + status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {/* Priority badge — monochrome */}
        <span
          style={{
            background: prio.bg,
            color: prio.text,
            fontSize: 9,
            fontWeight: 700,
            fontFamily: 'monospace',
            padding: '1px 4px',
            borderRadius: 2,
            minWidth: 18,
            textAlign: 'center',
            letterSpacing: 0.5,
          }}
        >
          P{task.priority}
        </span>

        {/* Phase symbol — no emoji */}
        <span style={{
          fontSize: 11,
          color: '#666',
          fontFamily: 'monospace',
          width: 12,
          textAlign: 'center',
        }}>{phaseSymbol}</span>

        {/* Title */}
        <span
          style={{
            flex: 1,
            fontSize: 12,
            color: '#ccc',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            fontWeight: 400,
          }}
        >
          {task.title}
        </span>

        {/* Status indicator — CSS, no emoji */}
        <StatusIndicator status={task.status} />
      </div>

      {/* Expanded view */}
      {expanded && (
        <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          {/* Description */}
          {task.description && task.description !== task.title && (
            <div style={{ fontSize: 11, color: '#777', marginBottom: 6, lineHeight: 1.4 }}>
              {task.description.slice(0, 200)}
              {task.description.length > 200 && '...'}
            </div>
          )}

          {/* Tags — monochrome pills */}
          {task.tags && task.tags.length > 0 && (
            <div style={{ display: 'flex', gap: 4, marginBottom: 6, flexWrap: 'wrap' }}>
              {task.tags.map((tag) => (
                <span
                  key={tag}
                  style={{
                    fontSize: 9,
                    background: 'rgba(255,255,255,0.06)',
                    color: '#888',
                    padding: '1px 6px',
                    borderRadius: 2,
                    fontFamily: 'monospace',
                    letterSpacing: 0.3,
                  }}
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Meta info */}
          <div style={{ fontSize: 10, color: '#555', marginBottom: 6, fontFamily: 'monospace' }}>
            {task.source && `src:${task.source}`}
            {task.preset && ` · ${task.preset}`}
            {task.created_at && ` · ${new Date(task.created_at).toLocaleTimeString()}`}
          </div>

          {/* Actions — dark monochrome buttons */}
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            {/* Priority selector */}
            {onPriorityChange && isDispatchable && (
              <select
                value={task.priority}
                onChange={(e) => {
                  e.stopPropagation();
                  onPriorityChange(task.id, parseInt(e.target.value));
                }}
                onClick={(e) => e.stopPropagation()}
                style={{
                  background: '#1a1a1a',
                  color: '#888',
                  border: '1px solid #333',
                  borderRadius: 3,
                  fontSize: 10,
                  fontFamily: 'monospace',
                  padding: '2px 4px',
                  outline: 'none',
                }}
              >
                <option value="1">P1</option>
                <option value="2">P2</option>
                <option value="3">P3</option>
                <option value="4">P4</option>
                <option value="5">P5</option>
              </select>
            )}

            {/* Dispatch button — Nolan minimal */}
            {onDispatch && isDispatchable && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDispatch(task.id);
                }}
                style={{
                  background: '#222',
                  color: '#e0e0e0',
                  border: '1px solid #444',
                  borderRadius: 3,
                  fontSize: 10,
                  fontFamily: 'monospace',
                  padding: '3px 10px',
                  cursor: 'pointer',
                  letterSpacing: 0.5,
                  textTransform: 'uppercase',
                  transition: 'all 0.15s',
                }}
              >
                run
              </button>
            )}

            {/* Remove button — subtle */}
            {onRemove && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRemove(task.id);
                }}
                style={{
                  background: 'transparent',
                  color: '#444',
                  border: '1px solid #333',
                  borderRadius: 3,
                  fontSize: 10,
                  padding: '2px 6px',
                  cursor: 'pointer',
                  marginLeft: 'auto',
                  transition: 'color 0.15s',
                }}
              >
                ✕
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
