/**
 * MARKER_181.5: PanelShell — compact CUT panel wrapper with window controls.
 * Supports docked + floating + mini modes, including all-edge floating resize.
 */
import { useCallback, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import { usePanelLayoutStore, type PanelId } from '../../store/usePanelLayoutStore';
import { useCutEditorStore } from '../../store/useCutEditorStore';

const IconDetach = ({ size = 12 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="2" y="5" width="8" height="8" rx="1" />
    <path d="M6 5V3a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1h-2" />
  </svg>
);

const IconDock = ({ size = 12 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="2" y="2" width="12" height="12" rx="1" />
    <path d="M2 6h12" />
  </svg>
);

const IconMinimize = ({ size = 12 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M3 8h10" />
  </svg>
);

const IconFullscreen = ({ size = 12 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M6 2H2v4M10 2h4v4M6 14H2v-4M10 14h4v-4" />
  </svg>
);

const IconClose = ({ size = 12 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M4 4l8 8M12 4l-8 8" />
  </svg>
);

const SHELL_DOCKED: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  width: '100%',
  height: '100%',
  background: '#171717',
  overflow: 'hidden',
};

const TITLE_BAR: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  height: 20,
  padding: '0 4px',
  background: '#101010',
  borderBottom: '0.5px solid #2c2c2c',
  userSelect: 'none',
  flexShrink: 0,
  cursor: 'default',
};

const TITLE_TEXT: CSSProperties = {
  fontSize: 9,
  fontFamily: 'Inter, system-ui, sans-serif',
  fontWeight: 500,
  color: '#8d8d8d',
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
  paddingRight: 4,
};

const TITLE_ACTIONS: CSSProperties = {
  display: 'flex',
  gap: 1,
  alignItems: 'center',
};

const ACTION_BTN: CSSProperties = {
  background: 'transparent',
  border: 'none',
  color: '#646464',
  cursor: 'pointer',
  width: 16,
  height: 16,
  borderRadius: 2,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 0,
};

const CONTENT: CSSProperties = {
  flex: 1,
  overflow: 'auto',
  minHeight: 0,
};

const floatingStyle = (x: number, y: number, w: number, h: number): CSSProperties => ({
  position: 'absolute',
  left: x,
  top: y,
  width: w,
  height: h,
  background: '#171717',
  border: '0.5px solid #303030',
  borderRadius: 4,
  boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
  zIndex: 100,
  display: 'flex',
  flexDirection: 'column',
  overflow: 'hidden',
});

const miniStyle = (x: number, y: number, w: number, h: number): CSSProperties => ({
  position: 'absolute',
  right: Math.abs(x),
  bottom: Math.abs(y),
  width: w,
  height: h,
  background: '#212121',
  border: '0.5px solid #333',
  borderRadius: 4,
  overflow: 'hidden',
  zIndex: 50,
  display: 'flex',
  flexDirection: 'column',
});

const PANEL_LABELS: Record<PanelId, string> = {
  script: 'Script',
  dag_project: 'DAG Project',
  project: 'Project',
  program_monitor: 'Program',
  source_monitor: 'Source',
  timeline: 'Timeline',
  story_space_3d: 'Story Space',
  effects: 'Effects',
  inspector: 'Inspector',
};

const PANEL_MIN_SIZE: Record<PanelId, { w: number; h: number }> = {
  script: { w: 220, h: 160 },
  dag_project: { w: 220, h: 160 },
  project: { w: 220, h: 160 },
  program_monitor: { w: 260, h: 180 },
  source_monitor: { w: 200, h: 150 },
  timeline: { w: 420, h: 120 },
  story_space_3d: { w: 180, h: 120 },
  effects: { w: 220, h: 140 },
  inspector: { w: 220, h: 140 },
};

interface PanelShellProps {
  panelId: PanelId;
  children: ReactNode;
  title?: string;
  hideTitleBar?: boolean;
}

type ResizeDir = 'n' | 's' | 'e' | 'w' | 'ne' | 'nw' | 'se' | 'sw';

// MARKER_W1.2: Map PanelId → focusedPanel store value
const PANEL_FOCUS_MAP: Partial<Record<PanelId, 'source' | 'program' | 'timeline' | 'project' | 'script' | 'dag'>> = {
  source_monitor: 'source',
  program_monitor: 'program',
  timeline: 'timeline',
  project: 'project',
  script: 'script',
  dag_project: 'dag',
};

export default function PanelShell({ panelId, children, title, hideTitleBar }: PanelShellProps) {
  const panel = usePanelLayoutStore((s) => s.getPanel(panelId));
  const detach = usePanelLayoutStore((s) => s.detach);
  const dock = usePanelLayoutStore((s) => s.dock);
  const togglePanel = usePanelLayoutStore((s) => s.togglePanel);
  const toggleMini = usePanelLayoutStore((s) => s.toggleMini);
  const moveFloating = usePanelLayoutStore((s) => s.moveFloating);
  const resizeFloating = usePanelLayoutStore((s) => s.resizeFloating);

  // MARKER_W1.2: Panel Focus
  const focusedPanel = useCutEditorStore((s) => s.focusedPanel);
  const setFocusedPanel = useCutEditorStore((s) => s.setFocusedPanel);
  const focusValue = PANEL_FOCUS_MAP[panelId] ?? null;
  const isFocused = focusValue !== null && focusedPanel === focusValue;
  const handleFocus = useCallback(() => {
    if (focusValue) setFocusedPanel(focusValue);
  }, [focusValue, setFocusedPanel]);

  const rootRef = useRef<HTMLDivElement | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const dragRef = useRef<{ startX: number; startY: number; origX: number; origY: number } | null>(null);
  const resizeRef = useRef<{
    dir: ResizeDir;
    startX: number;
    startY: number;
    x: number;
    y: number;
    w: number;
    h: number;
  } | null>(null);

  const minSize = PANEL_MIN_SIZE[panelId];
  const label = title || PANEL_LABELS[panelId] || panelId;

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    if (!panel || panel.mode !== 'floating' || !panel.floatGeometry) return;
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      origX: panel.floatGeometry.x,
      origY: panel.floatGeometry.y,
    };
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }, [panel]);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!dragRef.current) return;
    const dx = e.clientX - dragRef.current.startX;
    const dy = e.clientY - dragRef.current.startY;
    moveFloating(panelId, dragRef.current.origX + dx, dragRef.current.origY + dy);
  }, [moveFloating, panelId]);

  const handlePointerUp = useCallback(() => {
    dragRef.current = null;
  }, []);

  const handleResizeStart = useCallback((dir: ResizeDir, e: React.PointerEvent) => {
    if (!panel?.floatGeometry) return;
    e.stopPropagation();
    resizeRef.current = {
      dir,
      startX: e.clientX,
      startY: e.clientY,
      x: panel.floatGeometry.x,
      y: panel.floatGeometry.y,
      w: panel.floatGeometry.width,
      h: panel.floatGeometry.height,
    };
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }, [panel]);

  const handleResizeMove = useCallback((e: React.PointerEvent) => {
    const session = resizeRef.current;
    if (!session) return;
    e.stopPropagation();
    const dx = e.clientX - session.startX;
    const dy = e.clientY - session.startY;
    let nextX = session.x;
    let nextY = session.y;
    let nextW = session.w;
    let nextH = session.h;

    if (session.dir.includes('e')) nextW = Math.max(minSize.w, session.w + dx);
    if (session.dir.includes('s')) nextH = Math.max(minSize.h, session.h + dy);
    if (session.dir.includes('w')) {
      const rawW = session.w - dx;
      nextW = Math.max(minSize.w, rawW);
      nextX = session.x + (session.w - nextW);
    }
    if (session.dir.includes('n')) {
      const rawH = session.h - dy;
      nextH = Math.max(minSize.h, rawH);
      nextY = session.y + (session.h - nextH);
    }

    moveFloating(panelId, nextX, nextY);
    resizeFloating(panelId, nextW, nextH);
  }, [minSize.h, minSize.w, moveFloating, panelId, resizeFloating]);

  const handleResizeEnd = useCallback(() => {
    resizeRef.current = null;
  }, []);

  const handleToggleFullscreen = useCallback(async () => {
    const root = rootRef.current;
    if (!root) return;
    try {
      if (!document.fullscreenElement) {
        await root.requestFullscreen();
        setIsFullscreen(true);
      } else {
        await document.exitFullscreen();
        setIsFullscreen(false);
      }
    } catch {
      // no-op: browser may reject fullscreen gesture
    }
  }, []);

  const handleMinimize = useCallback(() => {
    if (panel?.mode === 'floating' || panel?.isMini) {
      toggleMini(panelId);
      return;
    }
    togglePanel(panelId);
  }, [panel, panelId, toggleMini, togglePanel]);

  if (!panel || !panel.visible) return null;

  if (panel.isMini && panel.floatGeometry) {
    const g = panel.floatGeometry;
    return (
      <div style={miniStyle(g.x, g.y, g.width, g.height)}>
        <div style={{ ...TITLE_BAR, height: 18 }}>
          <span style={{ ...TITLE_TEXT, fontSize: 8 }}>{label}</span>
          <div style={TITLE_ACTIONS}>
            <button style={ACTION_BTN} onClick={() => toggleMini(panelId)} title="Restore">
              <IconDock size={10} />
            </button>
          </div>
        </div>
        <div style={CONTENT}>{children}</div>
      </div>
    );
  }

  if (panel.mode === 'floating' && panel.floatGeometry) {
    const g = panel.floatGeometry;
    return (
      <div ref={rootRef} style={floatingStyle(g.x, g.y, g.width, g.height)}>
        <div
          style={{ ...TITLE_BAR, cursor: 'grab' }}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
        >
          <span style={TITLE_TEXT}>{label}</span>
          <div style={TITLE_ACTIONS}>
            <button style={ACTION_BTN} onClick={handleToggleFullscreen} title="Fullscreen">
              <IconFullscreen size={11} />
            </button>
            <button style={ACTION_BTN} onClick={handleMinimize} title="Minimize">
              <IconMinimize size={11} />
            </button>
            <button style={ACTION_BTN} onClick={() => dock(panelId, 'left')} title="Dock">
              <IconDock size={11} />
            </button>
            <button style={ACTION_BTN} onClick={() => togglePanel(panelId)} title="Close">
              <IconClose size={11} />
            </button>
          </div>
        </div>
        <div style={CONTENT}>{children}</div>
        {[
          { dir: 'n' as ResizeDir, style: { top: 0, left: 8, right: 8, height: 8, cursor: 'ns-resize' } },
          { dir: 's' as ResizeDir, style: { bottom: 0, left: 8, right: 8, height: 8, cursor: 'ns-resize' } },
          { dir: 'e' as ResizeDir, style: { right: 0, top: 8, bottom: 8, width: 8, cursor: 'ew-resize' } },
          { dir: 'w' as ResizeDir, style: { left: 0, top: 8, bottom: 8, width: 8, cursor: 'ew-resize' } },
          { dir: 'ne' as ResizeDir, style: { right: 0, top: 0, width: 12, height: 12, cursor: 'nesw-resize' } },
          { dir: 'nw' as ResizeDir, style: { left: 0, top: 0, width: 12, height: 12, cursor: 'nwse-resize' } },
          { dir: 'se' as ResizeDir, style: { right: 0, bottom: 0, width: 12, height: 12, cursor: 'nwse-resize' } },
          { dir: 'sw' as ResizeDir, style: { left: 0, bottom: 0, width: 12, height: 12, cursor: 'nesw-resize' } },
        ].map((handle) => (
          <div
            key={handle.dir}
            style={{ position: 'absolute', zIndex: 110, ...handle.style }}
            onPointerDown={(e) => handleResizeStart(handle.dir, e)}
            onPointerMove={handleResizeMove}
            onPointerUp={handleResizeEnd}
          />
        ))}
      </div>
    );
  }

  // MARKER_W1.2: Focus border style
  const focusBorder = isFocused ? { outline: '1px solid #4A9EFF', outlineOffset: -1 } : {};

  return (
    <div ref={rootRef} style={{ ...SHELL_DOCKED, ...focusBorder }} onMouseDown={handleFocus}>
      {!hideTitleBar && (
        <div style={TITLE_BAR}>
          <span style={TITLE_TEXT}>{label}</span>
          <div style={TITLE_ACTIONS}>
            <button style={ACTION_BTN} onClick={() => detach(panelId)} title="Detach">
              <IconDetach size={11} />
            </button>
            <button style={ACTION_BTN} onClick={handleToggleFullscreen} title="Fullscreen">
              <IconFullscreen size={11} />
            </button>
            <button style={ACTION_BTN} onClick={handleMinimize} title="Minimize">
              <IconMinimize size={11} />
            </button>
            <button style={ACTION_BTN} onClick={() => togglePanel(panelId)} title="Close">
              <IconClose size={11} />
            </button>
          </div>
        </div>
      )}
      <div style={CONTENT}>{children}</div>
      {isFullscreen ? null : null}
    </div>
  );
}
