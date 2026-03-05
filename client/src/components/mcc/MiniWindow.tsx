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

import { useState, useCallback, useRef, useEffect, type CSSProperties, type ReactNode } from 'react';
import Draggable from 'react-draggable';
import { motion, AnimatePresence } from 'framer-motion';
import { NOLAN_PALETTE } from '../../utils/dagLayout';

type Position = 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
type Size = { width: number; height: number };
type ResizeDirection = 'n' | 's' | 'e' | 'w' | 'ne' | 'nw' | 'se' | 'sw';
const LAYOUT_VERSION = 4;
const RESERVED_MINIMAP_WIDTH = 260;
const RESERVED_MINIMAP_HEIGHT = 190;
const PERSIST_POSITIONS = true;
const START_FROM_CENTER = false;
const MIN_WINDOW_WIDTH = 180;
const MIN_WINDOW_HEIGHT = 100;

function getViewportSize(): { width: number; height: number } {
  if (typeof window !== 'undefined') {
    return { width: window.innerWidth, height: window.innerHeight };
  }
  return { width: 1280, height: 800 };
}

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
  /** Explicit initial position override (diagnostic-safe). */
  initialPosition?: { x: number; y: number };
}

function storageKey(windowId: string): string {
  return `miniwindow_pos_v${LAYOUT_VERSION}_${windowId}`;
}

function sizeStorageKey(windowId: string): string {
  return `miniwindow_size_v${LAYOUT_VERSION}_${windowId}`;
}

function hasSavedPosition(windowId: string): boolean {
  if (!PERSIST_POSITIONS) return false;
  try {
    return Boolean(localStorage.getItem(storageKey(windowId)));
  } catch {
    return false;
  }
}

function hasSavedSize(windowId: string): boolean {
  if (!PERSIST_POSITIONS) return false;
  try {
    return Boolean(localStorage.getItem(sizeStorageKey(windowId)));
  } catch {
    return false;
  }
}

function clampSize(size: Size): Size {
  const padding = 12;
  const { width: vw, height: vh } = getViewportSize();
  const maxWidth = Math.max(MIN_WINDOW_WIDTH, vw - padding * 2);
  const maxHeight = Math.max(MIN_WINDOW_HEIGHT, vh - padding * 2);
  return {
    width: Math.min(Math.max(size.width, MIN_WINDOW_WIDTH), maxWidth),
    height: Math.min(Math.max(size.height, MIN_WINDOW_HEIGHT), maxHeight),
  };
}

// MARKER_155.DRAGGABLE.003: Default positions.
function getDefaultPosition(position: Position, width: number, height: number, windowId: string): { x: number; y: number } {
  const padding = 12;
  const { width: vw, height: vh } = getViewportSize();
  if (START_FROM_CENTER) {
    const cx = Math.max(padding, Math.round((vw - width) / 2));
    const cy = Math.max(padding, Math.round((vh - height) / 2));
    const offsetMap: Record<string, { dx: number; dy: number }> = {
      chat: { dx: -220, dy: -90 },
      stats: { dx: 20, dy: -90 },
      tasks: { dx: -100, dy: 90 },
    };
    const off = offsetMap[windowId] || { dx: 0, dy: 0 };
    return clampToViewport({ x: cx + off.dx, y: cy + off.dy }, width, height);
  }
  const maxX = Math.max(padding, vw - width - padding);
  const maxY = Math.max(padding, vh - height - padding);
  // Stack balance panel below stats in top-right on first placement.
  if (windowId === 'balance' && position === 'top-right') {
    return { x: maxX, y: Math.min(maxY, padding + 132) };
  }
  switch (position) {
    case 'top-left': return { x: padding, y: padding };
    case 'top-right': return { x: maxX, y: padding };
    case 'bottom-left': return { x: padding, y: maxY };
    case 'bottom-right': return { x: maxX, y: maxY };
  }
}

function clampToViewport(pos: { x: number; y: number }, width: number, height: number): { x: number; y: number } {
  const padding = 12;
  const { width: vw, height: vh } = getViewportSize();
  let next = {
    x: Math.min(Math.max(pos.x, padding), Math.max(padding, vw - width - padding)),
    y: Math.min(Math.max(pos.y, padding), Math.max(padding, vh - height - padding)),
  };

  // Keep bottom-right area free for DAG minimap preview.
  const reservedX = vw - RESERVED_MINIMAP_WIDTH - padding;
  const reservedY = vh - RESERVED_MINIMAP_HEIGHT - padding;
  if (next.x > reservedX && next.y > reservedY) {
    next = {
      x: Math.max(padding, reservedX - width - padding),
      y: next.y,
    };
  }
  return next;
}

// MARKER_155.DRAGGABLE.004: Load saved position from localStorage
function loadSavedPosition(windowId: string, defaultPos: { x: number; y: number }, width: number, height: number): { x: number; y: number } {
  if (!PERSIST_POSITIONS) return defaultPos;
  try {
    const saved = localStorage.getItem(storageKey(windowId));
    if (saved) {
      const parsed = JSON.parse(saved);
      return clampToViewport({ x: parsed.x, y: parsed.y }, width, height);
    }
  } catch {
    // Ignore errors
  }
  return defaultPos;
}

// MARKER_155.DRAGGABLE.005: Save position to localStorage
function savePosition(windowId: string, pos: { x: number; y: number }) {
  if (!PERSIST_POSITIONS) return;
  try {
    localStorage.setItem(storageKey(windowId), JSON.stringify(pos));
  } catch {
    // Ignore errors
  }
}

function loadSavedSize(windowId: string, defaultSize: Size): Size {
  if (!PERSIST_POSITIONS) return clampSize(defaultSize);
  try {
    const saved = localStorage.getItem(sizeStorageKey(windowId));
    if (saved) {
      const parsed = JSON.parse(saved);
      return clampSize({
        width: Number(parsed.width) || defaultSize.width,
        height: Number(parsed.height) || defaultSize.height,
      });
    }
  } catch {
    // Ignore errors
  }
  return clampSize(defaultSize);
}

function saveSize(windowId: string, size: Size) {
  if (!PERSIST_POSITIONS) return;
  try {
    localStorage.setItem(sizeStorageKey(windowId), JSON.stringify(size));
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
  initialPosition,
}: MiniWindowProps) {
  const initialSize = loadSavedSize(windowId, { width: compactWidth, height: compactHeight });
  const savedPositionRef = useRef<boolean>(hasSavedPosition(windowId));
  const savedSizeRef = useRef<boolean>(hasSavedSize(windowId));
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [sizeState, setSizeState] = useState<Size>(initialSize);
  const resizeSessionRef = useRef<{
    direction: ResizeDirection;
    startX: number;
    startY: number;
    startPosX: number;
    startPosY: number;
    startWidth: number;
    startHeight: number;
    nextPosX: number;
    nextPosY: number;
    nextWidth: number;
    nextHeight: number;
  } | null>(null);
  const [positionState, setPositionState] = useState(() =>
    loadSavedPosition(
      windowId,
      initialPosition || getDefaultPosition(position, initialSize.width, initialSize.height, windowId),
      initialSize.width,
      initialSize.height
    )
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
      const next = clampToViewport({ x: data.x, y: data.y }, sizeState.width, sizeState.height);
      setPositionState(next);
      savePosition(windowId, next);
    },
    [windowId, sizeState.width, sizeState.height]
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

  // MARKER_155F.MINIWINDOW.OPEN_EVENT_BIND.V1:
  // Allow other mini-windows (for example MiniChat model chip) to open/close this window by id.
  useEffect(() => {
    const handleWindowOpen = (event: Event) => {
      const detail = (event as CustomEvent)?.detail || {};
      if (String(detail.windowId || '') !== String(windowId)) return;
      const nextExpanded = detail.expanded !== undefined ? Boolean(detail.expanded) : true;
      setExpanded(nextExpanded);
      onToggle?.(nextExpanded);
    };
    window.addEventListener('mcc-miniwindow-open', handleWindowOpen as EventListener);
    return () => window.removeEventListener('mcc-miniwindow-open', handleWindowOpen as EventListener);
  }, [windowId, onToggle]);

  // Click outside to close (expanded only)
  const handleOverlayClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === overlayRef.current) collapse();
    },
    [collapse]
  );

  useEffect(() => {
    const onResize = () => {
      setSizeState((prev) => {
        const next = clampSize(prev);
        setPositionState((pos) => clampToViewport(pos, next.width, next.height));
        return next;
      });
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  useEffect(() => {
    if (savedPositionRef.current) return;
    const nextDefault = clampToViewport(
      initialPosition || getDefaultPosition(position, initialSize.width, initialSize.height, windowId),
      initialSize.width,
      initialSize.height
    );
    const rafId = window.requestAnimationFrame(() => {
      setPositionState(nextDefault);
    });
    return () => window.cancelAnimationFrame(rafId);
  }, [position, windowId, initialPosition, initialSize.width, initialSize.height]);

  useEffect(() => {
    if (savedSizeRef.current) return;
    const defaultSize = clampSize({ width: compactWidth, height: compactHeight });
    setSizeState(defaultSize);
  }, [compactWidth, compactHeight]);

  useEffect(() => {
    setPositionState((prev) => clampToViewport(prev, sizeState.width, sizeState.height));
  }, [sizeState.width, sizeState.height]);

  const handleResizeStart = useCallback((direction: ResizeDirection, e: React.MouseEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    resizeSessionRef.current = {
      direction,
      startX: e.clientX,
      startY: e.clientY,
      startPosX: positionState.x,
      startPosY: positionState.y,
      startWidth: sizeState.width,
      startHeight: sizeState.height,
      nextPosX: positionState.x,
      nextPosY: positionState.y,
      nextWidth: sizeState.width,
      nextHeight: sizeState.height,
    };
    setIsResizing(true);
  }, [positionState.x, positionState.y, sizeState.width, sizeState.height]);

  useEffect(() => {
    if (!isResizing) return;
    const onMove = (e: MouseEvent) => {
      const session = resizeSessionRef.current;
      if (!session) return;
      const dx = e.clientX - session.startX;
      const dy = e.clientY - session.startY;
      const padding = 12;
      const { width: vw, height: vh } = getViewportSize();
      let x = session.startPosX;
      let y = session.startPosY;
      let width = session.startWidth;
      let height = session.startHeight;

      if (session.direction.includes('e')) width = session.startWidth + dx;
      if (session.direction.includes('s')) height = session.startHeight + dy;
      if (session.direction.includes('w')) {
        width = session.startWidth - dx;
        x = session.startPosX + dx;
      }
      if (session.direction.includes('n')) {
        height = session.startHeight - dy;
        y = session.startPosY + dy;
      }

      if (width < MIN_WINDOW_WIDTH) {
        if (session.direction.includes('w')) x = session.startPosX + (session.startWidth - MIN_WINDOW_WIDTH);
        width = MIN_WINDOW_WIDTH;
      }
      if (height < MIN_WINDOW_HEIGHT) {
        if (session.direction.includes('n')) y = session.startPosY + (session.startHeight - MIN_WINDOW_HEIGHT);
        height = MIN_WINDOW_HEIGHT;
      }

      if (x < padding) {
        if (session.direction.includes('w')) width -= padding - x;
        x = padding;
      }
      if (y < padding) {
        if (session.direction.includes('n')) height -= padding - y;
        y = padding;
      }
      if (x + width > vw - padding) {
        if (session.direction.includes('e')) width = vw - padding - x;
        else x = vw - padding - width;
      }
      if (y + height > vh - padding) {
        if (session.direction.includes('s')) height = vh - padding - y;
        else y = vh - padding - height;
      }

      width = Math.max(width, MIN_WINDOW_WIDTH);
      height = Math.max(height, MIN_WINDOW_HEIGHT);

      const nextSize = clampSize({ width, height });
      const nextPos = clampToViewport({ x, y }, nextSize.width, nextSize.height);
      session.nextPosX = nextPos.x;
      session.nextPosY = nextPos.y;
      session.nextWidth = nextSize.width;
      session.nextHeight = nextSize.height;
      setPositionState(nextPos);
      setSizeState(nextSize);
    };
    const onUp = () => {
      const session = resizeSessionRef.current;
      if (session) {
        const finalSize = clampSize({ width: session.nextWidth, height: session.nextHeight });
        setSizeState(finalSize);
        const finalPos = clampToViewport({ x: session.nextPosX, y: session.nextPosY }, finalSize.width, finalSize.height);
        setPositionState(finalPos);
        savePosition(windowId, finalPos);
        saveSize(windowId, finalSize);
      }
      resizeSessionRef.current = null;
      setIsResizing(false);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [isResizing, windowId]);

  return (
    <>
      {/* MARKER_155.DRAGGABLE.008: Compact mode — draggable corner card */}
      {!expanded && (
        <Draggable
          nodeRef={nodeRef}
          position={positionState}
          onStart={handleDragStart}
          onStop={handleDragStop}
          disabled={isResizing}
          handle=".mini-window-grab"
          cancel="input,textarea,button,select,a,[data-no-drag='true']"
        >
          <div
            ref={nodeRef}
            className="mini-window-grab"
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              width: sizeState.width,
              height: sizeState.height,
              background: 'rgba(15,15,15,0.95)',
              backdropFilter: 'blur(12px)',
              border: `1px solid ${NOLAN_PALETTE.border}`,
              borderRadius: 8,
              overflow: 'hidden',
              zIndex: isDragging ? 420 : 360,
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
                  padding: '6px 8px',
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
                  overflow: 'auto',
                  padding: '4px 8px',
                  cursor: 'default',
                }}
              >
                {compactContent}
              </div>

              {([
                { dir: 'n', style: { top: 0, left: 10, right: 10, height: 6, cursor: 'ns-resize' } },
                { dir: 's', style: { bottom: 0, left: 10, right: 10, height: 6, cursor: 'ns-resize' } },
                { dir: 'e', style: { right: 0, top: 10, bottom: 10, width: 6, cursor: 'ew-resize' } },
                { dir: 'w', style: { left: 0, top: 10, bottom: 10, width: 6, cursor: 'ew-resize' } },
                { dir: 'ne', style: { right: 0, top: 0, width: 10, height: 10, cursor: 'nesw-resize' } },
                { dir: 'nw', style: { left: 0, top: 0, width: 10, height: 10, cursor: 'nwse-resize' } },
                { dir: 'se', style: { right: 0, bottom: 0, width: 10, height: 10, cursor: 'nwse-resize' } },
                { dir: 'sw', style: { left: 0, bottom: 0, width: 10, height: 10, cursor: 'nesw-resize' } },
              ] as Array<{ dir: ResizeDirection; style: CSSProperties }>).map((h) => (
                <div
                  key={h.dir}
                  data-no-drag="true"
                  onMouseDown={(e) => handleResizeStart(h.dir, e)}
                  style={{
                    position: 'absolute',
                    zIndex: 2,
                    background: 'transparent',
                    ...h.style,
                  }}
                />
              ))}
          </div>
        </Draggable>
      )}

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
              zIndex: 500,
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
