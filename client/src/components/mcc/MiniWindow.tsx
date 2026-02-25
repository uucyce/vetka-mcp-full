/**
 * MARKER_155.DRAGGABLE.002: MiniWindow — Draggable floating window framework.
 *
 * Uses react-draggable for position control.
 * Position is saved to localStorage per window.
 * Compact: small card in corner (draggable). Expanded: overlay (centered, not draggable).
 *
 * @phase 155
 * @wave 4
 * @status active
 */

import { useState, useCallback, useRef, useEffect, type ReactNode } from 'react';
import Draggable from 'react-draggable';
import { motion, AnimatePresence } from 'framer-motion';
import { NOLAN_PALETTE } from '../../utils/dagLayout';

type Position = 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';

interface MiniWindowProps {
  title: string;
  icon: string;
  position: Position;
  /** Unique ID for saving position to localStorage */
  windowId: string;
  /** Content for compact mode */
  compactContent: ReactNode;
  /** Content for expanded mode */
  expandedContent: ReactNode;
  /** Compact dimensions */
  compactWidth?: number;
  compactHeight?: number;
  /** Whether the window starts expanded */
  defaultExpanded?: boolean;
  /** External control */
  onToggle?: (expanded: boolean) => void;
}

// MARKER_155.DRAGGABLE.003: Default positions
function getDefaultPosition(position: Position, width: number): { x: number; y: number } {
  const padding = 8;
  switch (position) {
    case 'top-left': return { x: padding, y: padding };
    case 'top-right': return { x: window.innerWidth - width - padding, y: padding };
    case 'bottom-left': return { x: padding, y: window.innerHeight - 200 };
    case 'bottom-right': return { x: window.innerWidth - width - padding, y: window.innerHeight - 200 };
  }
}

// MARKER_155.DRAGGABLE.004: Load saved position from localStorage
function loadSavedPosition(windowId: string, defaultPos: { x: number; y: number }): { x: number; y: number } {
  try {
    const saved = localStorage.getItem(`miniwindow_pos_${windowId}`);
    if (saved) {
      const parsed = JSON.parse(saved);
      return { x: parsed.x, y: parsed.y };
    }
  } catch {
    // Ignore errors
  }
  return defaultPos;
}

// MARKER_155.DRAGGABLE.005: Save position to localStorage
function savePosition(windowId: string, pos: { x: number; y: number }) {
  try {
    localStorage.setItem(`miniwindow_pos_${windowId}`, JSON.stringify(pos));
  } catch {
    // Ignore errors
  }
}

export function MiniWindow({
  title,
  icon,
  position,
  windowId,
  compactContent,
  expandedContent,
  compactWidth = 200,
  compactHeight = 140,
  defaultExpanded = false,
  onToggle,
}: MiniWindowProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [isDragging, setIsDragging] = useState(false);
  const [positionState, setPositionState] = useState(() =>
    loadSavedPosition(windowId, getDefaultPosition(position, compactWidth))
  );
  const nodeRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  const toggle = useCallback(() => {
    const next = !expanded;
    setExpanded(next);
    onToggle?.(next);
  }, [expanded, onToggle]);

  const collapse = useCallback(() => {
    setExpanded(false);
    onToggle?.(false);
  }, [onToggle]);

  // MARKER_155.DRAGGABLE.006: Handle drag stop - save position
  const handleDragStop = useCallback(
    (_e: any, data: { x: number; y: number }) => {
      setIsDragging(false);
      setPositionState({ x: data.x, y: data.y });
      savePosition(windowId, { x: data.x, y: data.y });
    },
    [windowId]
  );

  // MARKER_155.DRAGGABLE.007: Handle drag start
  const handleDragStart = useCallback(() => {
    setIsDragging(true);
  }, []);

  // Close on Escape
  useEffect(() => {
    if (!expanded) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') collapse();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [expanded, collapse]);

  // Click outside to close (expanded only)
  const handleOverlayClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === overlayRef.current) collapse();
    },
    [collapse]
  );

  return (
    <>
      {/* MARKER_155.DRAGGABLE.008: Compact mode — draggable corner card */}
      <AnimatePresence>
        {!expanded && (
          <Draggable
            nodeRef={nodeRef}
            position={positionState}
            onStart={handleDragStart}
            onStop={handleDragStop}
            bounds="parent"
            handle=".mini-window-header"
          >
            <motion.div
              ref={nodeRef}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.2 }}
              style={{
                position: 'absolute',
                width: compactWidth,
                height: compactHeight,
                background: 'rgba(15,15,15,0.95)',
                backdropFilter: 'blur(12px)',
                border: `1px solid ${NOLAN_PALETTE.border}`,
                borderRadius: 8,
                overflow: 'hidden',
                zIndex: isDragging ? 100 : 50,
                fontFamily: 'monospace',
                display: 'flex',
                flexDirection: 'column',
                cursor: isDragging ? 'grabbing' : 'default',
                boxShadow: isDragging
                  ? '0 8px 32px rgba(0,0,0,0.4)'
                  : '0 2px 8px rgba(0,0,0,0.2)',
              }}
            >
              {/* MARKER_155.DRAGGABLE.009: Draggable header */}
              <div
                className="mini-window-header"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 5,
                  padding: '5px 8px',
                  cursor: 'grab',
                  borderBottom: `1px solid ${NOLAN_PALETTE.border}`,
                  flexShrink: 0,
                  background: isDragging ? 'rgba(74, 158, 255, 0.1)' : 'transparent',
                }}
              >
                <span style={{ fontSize: 10 }}>{icon}</span>
                <span
                  style={{
                    color: NOLAN_PALETTE.textAccent,
                    fontSize: 9,
                    fontWeight: 600,
                    flex: 1,
                  }}
                >
                  {title}
                </span>
                <button
                  onClick={toggle}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#444',
                    fontSize: 10,
                    cursor: 'pointer',
                    padding: '0 4px',
                  }}
                  title="Expand"
                >
                  ↗
                </button>
              </div>

              {/* Compact content */}
              <div
                style={{
                  flex: 1,
                  overflow: 'hidden',
                  padding: '4px 8px',
                  cursor: 'default',
                }}
              >
                {compactContent}
              </div>
            </motion.div>
          </Draggable>
        )}
      </AnimatePresence>

      {/* MARKER_155.DRAGGABLE.010: Expanded mode — centered overlay (not draggable) */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            ref={overlayRef}
            onClick={handleOverlayClick}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{
              position: 'absolute',
              inset: 0,
              background: 'rgba(0,0,0,0.5)',
              backdropFilter: 'blur(4px)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 80,
            }}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={{ duration: 0.25 }}
              style={{
                width: '80%',
                maxWidth: 700,
                height: '75%',
                maxHeight: 500,
                background: NOLAN_PALETTE.bgDim,
                border: `1px solid ${NOLAN_PALETTE.border}`,
                borderRadius: 10,
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
                fontFamily: 'monospace',
              }}
            >
              {/* Header */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '8px 14px',
                  borderBottom: `1px solid ${NOLAN_PALETTE.border}`,
                  flexShrink: 0,
                }}
              >
                <span style={{ fontSize: 13 }}>{icon}</span>
                <span
                  style={{
                    color: NOLAN_PALETTE.text,
                    fontSize: 12,
                    fontWeight: 600,
                    flex: 1,
                  }}
                >
                  {title}
                </span>
                <button
                  onClick={collapse}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: NOLAN_PALETTE.textMuted,
                    cursor: 'pointer',
                    fontSize: 14,
                    padding: '0 4px',
                  }}
                  title="Collapse"
                >
                  ↙
                </button>
                <button
                  onClick={collapse}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: NOLAN_PALETTE.textMuted,
                    cursor: 'pointer',
                    fontSize: 14,
                    padding: '0 4px',
                  }}
                  title="Close"
                >
                  ✕
                </button>
              </div>

              {/* Expanded content */}
              <div style={{ flex: 1, overflow: 'auto' }}>{expandedContent}</div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
