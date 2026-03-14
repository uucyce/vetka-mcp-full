/**
 * FloatingWindow - Draggable and resizable window component.
 * Uses react-rnd for window positioning and sizing.
 *
 * @status active
 * @phase 96
 * @depends react-rnd, lucide-react, react
 * @used_by ArtifactWindow, ChatPanel
 */

import { Rnd } from 'react-rnd';
import { X, Maximize2 } from 'lucide-react';
import { useState, useCallback } from 'react';

interface Props {
  title: string;
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
  defaultWidth?: number;
  defaultHeight?: number;
  headerActions?: React.ReactNode;
}

export function FloatingWindow({
  title,
  isOpen,
  onClose,
  children,
  defaultWidth = 600,
  defaultHeight = 500,
  headerActions,
}: Props) {
  const [isMaximized, setIsMaximized] = useState(false);
  const [size, setSize] = useState({ width: defaultWidth, height: defaultHeight });
  const [position, setPosition] = useState({ x: 100, y: 100 });
  const [prevState, setPrevState] = useState({ size, position });

  const toggleMaximize = useCallback(() => {
    if (isMaximized) {
      setSize(prevState.size);
      setPosition(prevState.position);
      setIsMaximized(false);
    } else {
      setPrevState({ size, position });
      setSize({ width: window.innerWidth - 100, height: window.innerHeight - 100 });
      setPosition({ x: 50, y: 50 });
      setIsMaximized(true);
    }
  }, [isMaximized, size, position, prevState]);

  if (!isOpen) return null;

  return (
    <Rnd
      size={isMaximized ? { width: size.width, height: size.height } : size}
      position={isMaximized ? { x: position.x, y: position.y } : position}
      onDragStop={(_, d) => {
        if (!isMaximized) setPosition({ x: d.x, y: d.y });
      }}
      onResizeStop={(_, __, ref, ___, pos) => {
        if (!isMaximized) {
          setSize({ width: ref.offsetWidth, height: ref.offsetHeight });
          setPosition(pos);
        }
      }}
      minWidth={300}
      minHeight={200}
      dragHandleClassName="window-drag-handle"
      enableResizing={!isMaximized}
      style={{
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: '#0f0f0f',
        borderRadius: 8,
        border: '1px solid #333',
        boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
        overflow: 'hidden',
      }}>
        {/* Title bar */}
        <div
          className="window-drag-handle"
          style={{
            display: 'flex',
            alignItems: 'center',
            padding: '8px 12px',
            background: '#1a1a1a',
            borderBottom: '1px solid #333',
            cursor: 'move',
          }}
        >
          <div style={{
            flex: 1,
            fontSize: 13,
            fontWeight: 500,
            color: '#e0e0e0',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}>
            {title}
          </div>

          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            {headerActions}
            <button
              onClick={toggleMaximize}
              style={{
                padding: 4,
                background: 'transparent',
                border: 'none',
                borderRadius: 4,
                color: '#666',
                cursor: 'pointer',
              }}
              title="Maximize"
            >
              <Maximize2 size={14} />
            </button>
            <button
              onClick={onClose}
              style={{
                padding: 4,
                background: 'transparent',
                border: 'none',
                borderRadius: 4,
                color: '#666',
                cursor: 'pointer',
              }}
              title="Close"
            >
              <X size={14} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div style={{
          flex: 1,
          overflow: 'hidden',
        }}>
          {children}
        </div>
      </div>
    </Rnd>
  );
}
