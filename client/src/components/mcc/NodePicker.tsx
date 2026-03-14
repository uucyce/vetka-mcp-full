import { memo, useEffect, useMemo, useRef, useState } from 'react';
import { NOLAN_PALETTE } from '../../utils/dagLayout';
import type { DAGNodeType } from '../../types/dag';

const NODE_TYPES: Array<{ type: DAGNodeType; label: string; icon: string }> = [
  { type: 'task', label: 'Task', icon: '■' },
  { type: 'agent', label: 'Agent', icon: '●' },
  { type: 'condition', label: 'Condition', icon: '◇' },
  { type: 'parallel', label: 'Parallel', icon: '⫸' },
  { type: 'loop', label: 'Loop', icon: '↻' },
  { type: 'transform', label: 'Transform', icon: '⟐' },
  { type: 'group', label: 'Group', icon: '⊞' },
];

interface NodePickerProps {
  position: { x: number; y: number } | null;
  onClose: () => void;
  onSelect: (type: DAGNodeType, position: { x: number; y: number }) => void;
}

function NodePickerComponent({ position, onClose, onSelect }: NodePickerProps) {
  const [query, setQuery] = useState('');
  const [activeIdx, setActiveIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!position) return;
    setQuery('');
    setActiveIdx(0);
    setTimeout(() => inputRef.current?.focus(), 0);
  }, [position]);

  useEffect(() => {
    if (!position) return;
    const onMouseDown = (e: MouseEvent) => {
      if (popupRef.current && !popupRef.current.contains(e.target as Node)) onClose();
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('mousedown', onMouseDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onMouseDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [position, onClose]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return NODE_TYPES;
    return NODE_TYPES.filter((n) => n.label.toLowerCase().includes(q) || n.type.toLowerCase().includes(q));
  }, [query]);

  useEffect(() => {
    if (activeIdx >= filtered.length) setActiveIdx(0);
  }, [activeIdx, filtered.length]);

  if (!position) return null;

  return (
    <div
      ref={popupRef}
      style={{
        position: 'fixed',
        left: position.x,
        top: position.y,
        zIndex: 1200,
        width: 230,
        background: '#131313',
        border: `1px solid ${NOLAN_PALETTE.border}`,
        borderRadius: 6,
        boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
        overflow: 'hidden',
        fontFamily: 'monospace',
      }}
    >
      <input
        ref={inputRef}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown') {
            e.preventDefault();
            setActiveIdx((i) => Math.min(filtered.length - 1, i + 1));
          } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setActiveIdx((i) => Math.max(0, i - 1));
          } else if (e.key === 'Enter') {
            e.preventDefault();
            const candidate = filtered[activeIdx];
            if (candidate) {
              onSelect(candidate.type, position);
              onClose();
            }
          }
        }}
        placeholder="Search node type..."
        style={{
          width: '100%',
          border: 'none',
          borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
          background: '#101010',
          color: '#ddd',
          padding: '8px 10px',
          fontSize: 10,
          fontFamily: 'monospace',
          outline: 'none',
        }}
      />

      <div style={{ maxHeight: 210, overflowY: 'auto', padding: '6px 0' }}>
        {filtered.map((node, idx) => {
          const active = idx === activeIdx;
          return (
            <button
              key={node.type}
              onMouseEnter={() => setActiveIdx(idx)}
              onClick={() => {
                onSelect(node.type, position);
                onClose();
              }}
              style={{
                width: '100%',
                textAlign: 'left',
                border: 'none',
                background: active ? '#1d1d1d' : 'transparent',
                color: active ? '#e5fffb' : '#c6c6c6',
                padding: '6px 10px',
                fontSize: 10,
                fontFamily: 'monospace',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                cursor: 'pointer',
              }}
            >
              <span style={{ width: 12, textAlign: 'center', color: active ? '#4ecdc4' : '#888' }}>{node.icon}</span>
              <span>{node.label}</span>
            </button>
          );
        })}
        {filtered.length === 0 && (
          <div style={{ padding: '8px 10px', color: '#777', fontSize: 10 }}>No matches</div>
        )}
      </div>
    </div>
  );
}

export const NodePicker = memo(NodePickerComponent);

