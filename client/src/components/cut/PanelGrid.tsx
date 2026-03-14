/**
 * MARKER_181.3: PanelGrid — CSS Grid layout for VETKA CUT (IKEA-Premiere).
 *
 * Default: left 260px (split top/bottom) | center flex | right 280px (split top/bottom) | bottom ~35%
 * All borders resizable by dragging. Free windows, not fixed zones.
 *
 * Architecture doc: PREMIERE_LAYOUT_ARCHITECTURE.md §4
 */
import { useCallback, useRef, type CSSProperties, type ReactNode } from 'react';
import { usePanelLayoutStore, type DockPosition } from '../../store/usePanelLayoutStore';

// ─── Styles (§11 compliant) ───

const GRID_ROOT: CSSProperties = {
  display: 'grid',
  width: '100%',
  height: '100%',
  background: '#0D0D0D',
  overflow: 'hidden',
  gap: 0,
};

const RESIZE_HANDLE_V: CSSProperties = {
  width: 3,
  cursor: 'col-resize',
  background: '#1A1A1A',
  transition: 'background 0.15s',
  flexShrink: 0,
  zIndex: 10,
};

const RESIZE_HANDLE_H: CSSProperties = {
  height: 3,
  cursor: 'row-resize',
  background: '#1A1A1A',
  transition: 'background 0.15s',
  flexShrink: 0,
  zIndex: 10,
  gridColumn: '1 / -1',
};

const CELL: CSSProperties = {
  overflow: 'hidden',
  position: 'relative',
  minWidth: 0,
  minHeight: 0,
};

// ─── Types ───

interface PanelGridProps {
  /** Render function: returns panel content for a dock position */
  renderPanel: (position: DockPosition) => ReactNode;
  /** Optional: floating panels overlay */
  floatingPanels?: ReactNode;
}

/**
 * PanelGrid renders the IKEA-Premiere layout:
 *
 *   ┌──────────┬─────────────────┬──────────┐
 *   │  LEFT    │     CENTER      │  RIGHT   │
 *   │  TOP     │  (Program Mon.) │  TOP     │
 *   │(Src Mon.)│                 │(Prg Mon.)│
 *   ├──────────┤                 ├──────────┤
 *   │  LEFT    │                 │  RIGHT   │
 *   │  BOTTOM  │                 │  BOTTOM  │
 *   │(Project) │                 │(Insp/Tab)│
 *   ├──────────┴─────────────────┴──────────┤
 *   │          BOTTOM (~35% — Timeline)      │
 *   └───────────────────────────────────────┘
 */
export default function PanelGrid({ renderPanel, floatingPanels }: PanelGridProps) {
  const grid = usePanelLayoutStore((s) => s.grid);
  const setGridSize = usePanelLayoutStore((s) => s.setGridSize);

  // ─── Resize handlers ───
  const leftResizeRef = useRef<{ startX: number; startWidth: number } | null>(null);
  const rightResizeRef = useRef<{ startX: number; startWidth: number } | null>(null);
  const bottomResizeRef = useRef<{ startY: number; startHeight: number } | null>(null);
  const rightSplitResizeRef = useRef<{ startY: number; startSplit: number; containerHeight: number } | null>(null);

  const handleLeftResizeDown = useCallback(
    (e: React.PointerEvent) => {
      leftResizeRef.current = { startX: e.clientX, startWidth: grid.leftWidth };
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    },
    [grid.leftWidth],
  );

  const handleLeftResizeMove = useCallback(
    (e: React.PointerEvent) => {
      if (!leftResizeRef.current) return;
      const dx = e.clientX - leftResizeRef.current.startX;
      setGridSize('leftWidth', Math.max(120, Math.min(500, leftResizeRef.current.startWidth + dx)));
    },
    [setGridSize],
  );

  const handleRightResizeDown = useCallback(
    (e: React.PointerEvent) => {
      rightResizeRef.current = { startX: e.clientX, startWidth: grid.rightWidth };
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    },
    [grid.rightWidth],
  );

  const handleRightResizeMove = useCallback(
    (e: React.PointerEvent) => {
      if (!rightResizeRef.current) return;
      const dx = e.clientX - rightResizeRef.current.startX;
      setGridSize('rightWidth', Math.max(160, Math.min(600, rightResizeRef.current.startWidth - dx)));
    },
    [setGridSize],
  );

  const handleBottomResizeDown = useCallback(
    (e: React.PointerEvent) => {
      bottomResizeRef.current = { startY: e.clientY, startHeight: grid.bottomHeight };
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    },
    [grid.bottomHeight],
  );

  const handleBottomResizeMove = useCallback(
    (e: React.PointerEvent) => {
      if (!bottomResizeRef.current) return;
      const dy = e.clientY - bottomResizeRef.current.startY;
      // Bottom panel grows when dragging up (negative dy)
      setGridSize('bottomHeight', Math.max(120, Math.min(700, bottomResizeRef.current.startHeight - dy)));
    },
    [setGridSize],
  );

  const handleRightSplitResizeDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      const parent = e.currentTarget.parentElement;
      const containerHeight = Math.max(1, parent?.clientHeight || 1);
      rightSplitResizeRef.current = { startY: e.clientY, startSplit: grid.rightSplit, containerHeight };
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    },
    [grid.rightSplit],
  );

  const handleRightSplitResizeMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!rightSplitResizeRef.current) return;
      const dy = e.clientY - rightSplitResizeRef.current.startY;
      const nextSplit = rightSplitResizeRef.current.startSplit + (dy / rightSplitResizeRef.current.containerHeight);
      setGridSize('rightSplit', Math.max(0.2, Math.min(0.8, nextSplit)));
    },
    [setGridSize],
  );

  const handleResizeUp = useCallback(() => {
    leftResizeRef.current = null;
    rightResizeRef.current = null;
    bottomResizeRef.current = null;
    rightSplitResizeRef.current = null;
  }, []);

  // Column splits (top/bottom within each side column)
  const leftTopH = `${grid.leftSplit * 100}%`;
  const leftBottomH = `${(1 - grid.leftSplit) * 100}%`;
  const rightTopH = `${grid.rightSplit * 100}%`;
  const rightBottomH = `${(1 - grid.rightSplit) * 100}%`;

  const gridTemplate = {
    gridTemplateColumns: `${grid.leftWidth}px 3px 1fr 3px ${grid.rightWidth}px`,
    gridTemplateRows: `1fr 3px ${grid.bottomHeight}px`,
  };

  return (
    <div style={{ ...GRID_ROOT, ...gridTemplate, position: 'relative' }}>
      {/* Row 1: Left | resize | Center | resize | Right */}

      {/* Left column — split into top (Source Monitor) + bottom (Project) */}
      <div style={{ ...CELL, gridColumn: '1', gridRow: '1', display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: leftTopH, overflow: 'hidden', minHeight: 0 }}>
          {renderPanel('left_top')}
        </div>
        <div
          style={{
            height: 3,
            cursor: 'row-resize',
            background: '#1A1A1A',
            flexShrink: 0,
          }}
        />
        <div style={{ flex: leftBottomH, overflow: 'hidden', minHeight: 0 }}>
          {renderPanel('left_bottom')}
        </div>
      </div>

      {/* Left resize handle */}
      <div
        style={{ ...RESIZE_HANDLE_V, gridColumn: '2', gridRow: '1' }}
        onPointerDown={handleLeftResizeDown}
        onPointerMove={handleLeftResizeMove}
        onPointerUp={handleResizeUp}
      />

      {/* Center column — Program Monitor (future: can hold any docked panel) */}
      <div style={{ ...CELL, gridColumn: '3', gridRow: '1' }}>
        {renderPanel('center')}
      </div>

      {/* Right resize handle */}
      <div
        style={{ ...RESIZE_HANDLE_V, gridColumn: '4', gridRow: '1' }}
        onPointerDown={handleRightResizeDown}
        onPointerMove={handleRightResizeMove}
        onPointerUp={handleResizeUp}
      />

      {/* Right column — split into top (Program Monitor) + bottom (Inspector + tabs) */}
      <div style={{ ...CELL, gridColumn: '5', gridRow: '1', display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: rightTopH, overflow: 'hidden', minHeight: 0 }}>
          {renderPanel('right_top')}
        </div>
        <div
          style={{
            height: 3,
            cursor: 'row-resize',
            background: '#1A1A1A',
            flexShrink: 0,
          }}
          onPointerDown={handleRightSplitResizeDown}
          onPointerMove={handleRightSplitResizeMove}
          onPointerUp={handleResizeUp}
        />
        <div style={{ flex: rightBottomH, overflow: 'hidden', minHeight: 0 }}>
          {renderPanel('right_bottom')}
        </div>
      </div>

      {/* Row 2: Bottom resize handle (full width) */}
      <div
        style={{ ...RESIZE_HANDLE_H, gridRow: '2' }}
        onPointerDown={handleBottomResizeDown}
        onPointerMove={handleBottomResizeMove}
        onPointerUp={handleResizeUp}
      />

      {/* Row 3: Bottom (Timeline) — full width */}
      <div style={{ ...CELL, gridColumn: '1 / -1', gridRow: '3' }}>
        {renderPanel('bottom')}
      </div>

      {/* Floating panels overlay */}
      {floatingPanels}
    </div>
  );
}
