/**
 * MARKER_144.3: DAG Context Menu — right-click on canvas/node/edge.
 * Only visible when editMode=true.
 * Nolan palette, monospace, compact.
 *
 * @phase 144
 * @status active
 */

import { memo, useEffect, useRef } from 'react';
import { NOLAN_PALETTE } from '../../utils/dagLayout';
import type { DAGNodeType } from '../../types/dag';

// Node types available for creation
const CREATABLE_NODE_TYPES: { type: DAGNodeType; label: string; icon: string }[] = [
  { type: 'task', label: 'Task', icon: '■' },
  { type: 'agent', label: 'Agent', icon: '●' },
  { type: 'condition', label: 'Condition', icon: '◇' },
  { type: 'parallel', label: 'Parallel', icon: '⫸' },
  { type: 'loop', label: 'Loop', icon: '↻' },
  { type: 'transform', label: 'Transform', icon: '⟐' },
  { type: 'group', label: 'Group', icon: '⊞' },
];

export type ContextMenuTarget =
  | { kind: 'canvas'; position: { x: number; y: number } }
  | { kind: 'node'; nodeId: string; position: { x: number; y: number } }
  | { kind: 'edge'; edgeId: string; position: { x: number; y: number } };

interface DAGContextMenuProps {
  target: ContextMenuTarget | null;
  onClose: () => void;
  onAddNode: (type: DAGNodeType, position: { x: number; y: number }) => void;
  onCreateTaskHere?: (nodeId: string, position: { x: number; y: number }) => void;
  onDeleteNode?: (nodeId: string) => void;
  onDuplicateNode?: (nodeId: string) => void;
  onDeleteEdge?: (edgeId: string) => void;
}

const menuStyle: React.CSSProperties = {
  position: 'fixed',
  zIndex: 1000,
  background: NOLAN_PALETTE.bgLight,
  border: `1px solid ${NOLAN_PALETTE.border}`,
  borderRadius: 4,
  padding: '4px 0',
  minWidth: 160,
  fontFamily: 'monospace',
  fontSize: 11,
  color: NOLAN_PALETTE.text,
  boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
};

const itemStyle: React.CSSProperties = {
  padding: '5px 12px',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  transition: 'background 0.1s',
};

const separatorStyle: React.CSSProperties = {
  height: 1,
  background: NOLAN_PALETTE.border,
  margin: '4px 0',
};

const subMenuLabelStyle: React.CSSProperties = {
  padding: '3px 12px',
  fontSize: 9,
  color: NOLAN_PALETTE.textDim,
  textTransform: 'uppercase' as const,
  letterSpacing: '0.5px',
};

function DAGContextMenuComponent({
  target,
  onClose,
  onAddNode,
  onCreateTaskHere,
  onDeleteNode,
  onDuplicateNode,
  onDeleteEdge,
}: DAGContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on click outside or Escape
  useEffect(() => {
    if (!target) return;

    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKey);
    };
  }, [target, onClose]);

  if (!target) return null;

  const { position } = target;

  const handleItemHover = (e: React.MouseEvent<HTMLDivElement>) => {
    (e.currentTarget as HTMLDivElement).style.background = NOLAN_PALETTE.bgDim;
  };
  const handleItemLeave = (e: React.MouseEvent<HTMLDivElement>) => {
    (e.currentTarget as HTMLDivElement).style.background = 'transparent';
  };

  return (
    <div
      ref={menuRef}
      style={{
        ...menuStyle,
        left: position.x,
        top: position.y,
      }}
    >
      {/* Canvas context menu — add new nodes */}
      {target.kind === 'canvas' && (
        <>
          <div style={subMenuLabelStyle}>add node</div>
          {CREATABLE_NODE_TYPES.map(({ type, label, icon }) => (
            <div
              key={type}
              style={itemStyle}
              onMouseEnter={handleItemHover}
              onMouseLeave={handleItemLeave}
              onClick={() => {
                onAddNode(type, target.position);
                onClose();
              }}
            >
              <span style={{ width: 14, textAlign: 'center' }}>{icon}</span>
              <span>{label}</span>
            </div>
          ))}
        </>
      )}

      {/* Node context menu */}
      {target.kind === 'node' && (
        <>
          {onCreateTaskHere && (
            <div
              style={itemStyle}
              onMouseEnter={handleItemHover}
              onMouseLeave={handleItemLeave}
              onClick={() => {
                onCreateTaskHere(target.nodeId, target.position);
                onClose();
              }}
            >
              <span style={{ width: 14, textAlign: 'center' }}>+</span>
              <span>Create Task Here</span>
            </div>
          )}
          {onDuplicateNode && (
            <>
              {onCreateTaskHere && <div style={separatorStyle} />}
            <div
              style={itemStyle}
              onMouseEnter={handleItemHover}
              onMouseLeave={handleItemLeave}
              onClick={() => {
                onDuplicateNode(target.nodeId);
                onClose();
              }}
            >
              <span style={{ width: 14, textAlign: 'center' }}>⧉</span>
              <span>Duplicate</span>
            </div>
            </>
          )}
          {onDeleteNode && (
            <>
              <div style={separatorStyle} />
              <div
                style={{ ...itemStyle, color: NOLAN_PALETTE.textDim }}
                onMouseEnter={handleItemHover}
                onMouseLeave={handleItemLeave}
                onClick={() => {
                  onDeleteNode(target.nodeId);
                  onClose();
                }}
              >
                <span style={{ width: 14, textAlign: 'center' }}>✕</span>
                <span>Delete</span>
              </div>
            </>
          )}
        </>
      )}

      {/* Edge context menu */}
      {target.kind === 'edge' && (
        <>
          {onDeleteEdge && (
            <div
              style={{ ...itemStyle, color: NOLAN_PALETTE.textDim }}
              onMouseEnter={handleItemHover}
              onMouseLeave={handleItemLeave}
              onClick={() => {
                onDeleteEdge(target.edgeId);
                onClose();
              }}
            >
              <span style={{ width: 14, textAlign: 'center' }}>✕</span>
              <span>Delete Edge</span>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export const DAGContextMenu = memo(DAGContextMenuComponent);
