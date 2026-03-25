/**
 * Reusable panel component with collapsible and resizable features.
 *
 * @status active
 * @phase 96
 * @depends react
 * @used_by ./FilePreview, ./components/chat/ChatSidebar
 */
import { ReactNode, useState, useCallback } from 'react';

interface PanelProps {
  title: string;
  children: ReactNode;
  position: 'left' | 'right';
  defaultWidth?: number;
  minWidth?: number;
  maxWidth?: number;
  collapsible?: boolean;
  defaultCollapsed?: boolean;
  resizable?: boolean;
}

export function Panel({
  title,
  children,
  position,
  defaultWidth = 400,
  minWidth = 200,
  maxWidth = 800,
  collapsible = true,
  defaultCollapsed = false,
  resizable = true,
}: PanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [width, setWidth] = useState(defaultWidth);
  const [isResizing, setIsResizing] = useState(false);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (!resizable) return;
      e.preventDefault();
      setIsResizing(true);

      const startX = e.clientX;
      const startWidth = width;

      const handleMouseMove = (moveEvent: MouseEvent) => {
        const delta =
          position === 'left'
            ? moveEvent.clientX - startX
            : startX - moveEvent.clientX;
        const newWidth = Math.min(maxWidth, Math.max(minWidth, startWidth + delta));
        setWidth(newWidth);
      };

      const handleMouseUp = () => {
        setIsResizing(false);
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    },
    [resizable, width, position, minWidth, maxWidth]
  );

  const handleResizeHover = useCallback(
    (e: React.MouseEvent<HTMLDivElement>, isHovering: boolean) => {
      if (!isResizing) {
        e.currentTarget.style.background = isHovering ? '#374151' : 'transparent';
      }
    },
    [isResizing]
  );

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        bottom: 0,
        [position]: 0,
        width: isCollapsed ? 48 : width,
        background: 'rgba(17, 24, 39, 0.95)',
        borderLeft: position === 'right' ? '1px solid #374151' : 'none',
        borderRight: position === 'left' ? '1px solid #374151' : 'none',
        display: 'flex',
        flexDirection: 'column',
        transition: isResizing ? 'none' : 'width 0.2s ease',
        zIndex: 100,
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid #374151',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          minHeight: 48,
        }}
      >
        {!isCollapsed && (
          <span style={{ color: '#f3f4f6', fontWeight: 600, fontSize: 14 }}>{title}</span>
        )}
        {collapsible && (
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            style={{
              background: 'none',
              border: 'none',
              color: '#9ca3af',
              cursor: 'pointer',
              fontSize: 18,
              padding: 4,
              marginLeft: isCollapsed ? 'auto' : 0,
              marginRight: isCollapsed ? 'auto' : 0,
            }}
          >
            {isCollapsed
              ? position === 'left'
                ? '\u2192'
                : '\u2190'
              : position === 'left'
                ? '\u2190'
                : '\u2192'}
          </button>
        )}
      </div>

      {/* Content */}
      <div
        style={{
          flex: 1,
          overflow: 'auto',
          padding: isCollapsed ? 0 : 16,
          display: isCollapsed ? 'none' : 'block',
        }}
      >
        {children}
      </div>

      {/* Resize handle */}
      {resizable && !isCollapsed && (
        <div
          onMouseDown={handleMouseDown}
          onMouseEnter={(e) => handleResizeHover(e, true)}
          onMouseLeave={(e) => handleResizeHover(e, false)}
          style={{
            position: 'absolute',
            top: 0,
            bottom: 0,
            [position === 'left' ? 'right' : 'left']: 0,
            width: 4,
            cursor: 'col-resize',
            background: isResizing ? '#555' : 'transparent',
          }}
        />
      )}
    </div>
  );
}
