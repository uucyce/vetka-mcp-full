/**
 * MARKER_180.2: PanelShell — universal wrapper for all CUT panels.
 * Supports 3 modes: docked, tab, floating.
 * Title bar with tab/detach/close buttons. Drag handle for floating.
 * Monochrome SVG icons per Architecture doc §11.
 *
 * Architecture doc §1: "Every panel can be a tab inside another panel
 * OR a standalone floating window. User drags to detach, drops to dock."
 */
import { useCallback, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import { usePanelLayoutStore, type PanelId, type PanelMode } from '../../store/usePanelLayoutStore';

// ─── Monochrome SVG Icons (§11: stroke only, 1.5px, no fill) ───

const IconDetach = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="2" y="5" width="8" height="8" rx="1" />
    <path d="M6 5V3a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1h-2" />
  </svg>
);

const IconDock = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="2" y="2" width="12" height="12" rx="1" />
    <path d="M2 6h12" />
  </svg>
);

const IconClose = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M4 4l8 8M12 4l-8 8" />
  </svg>
);

const IconExpand = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M10 2h4v4M6 14H2v-4M14 2L9 7M2 14l5-5" />
  </svg>
);

const IconCollapse = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M6 10H2v4M10 6h4V2M2 14l5-5M14 2l-5 5" />
  </svg>
);

// ─── Styles (§11 compliant: dark, flat, no gradients) ───

const SHELL_DOCKED: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  width: '100%',
  height: '100%',
  background: '#1A1A1A',
  overflow: 'hidden',
};

const TITLE_BAR: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  height: 24,
  padding: '0 6px',
  background: '#141414',
  borderBottom: '0.5px solid #333',
  userSelect: 'none',
  flexShrink: 0,
  cursor: 'default',
};

const TITLE_TEXT: CSSProperties = {
  fontSize: 10,
  fontFamily: 'Inter, system-ui, sans-serif',
  fontWeight: 500,
  color: '#888',
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
};

const TITLE_ACTIONS: CSSProperties = {
  display: 'flex',
  gap: 2,
  alignItems: 'center',
};

const ACTION_BTN: CSSProperties = {
  background: 'transparent',
  border: 'none',
  color: '#555',
  cursor: 'pointer',
  padding: 2,
  borderRadius: 2,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  transition: 'color 0.15s',
};

const CONTENT: CSSProperties = {
  flex: 1,
  overflow: 'auto',
  minHeight: 0,
};

// ─── Floating shell styles ───

const floatingStyle = (x: number, y: number, w: number, h: number): CSSProperties => ({
  position: 'absolute',
  left: x,
  top: y,
  width: w,
  height: h,
  background: '#1A1A1A',
  border: '0.5px solid #333',
  borderRadius: 4,
  boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
  zIndex: 100,
  display: 'flex',
  flexDirection: 'column',
  overflow: 'hidden',
});

const FLOATING_TITLE_BAR: CSSProperties = {
  ...TITLE_BAR,
  cursor: 'grab',
};

// ─── Mini shell (StorySpace3D vectorscope) ───

const miniStyle = (x: number, y: number, w: number, h: number): CSSProperties => ({
  position: 'absolute',
  right: Math.abs(x),
  bottom: Math.abs(y),
  width: w,
  height: h,
  background: '#252525',
  border: '0.5px solid #333',
  borderRadius: 4,
  overflow: 'hidden',
  zIndex: 50,
  display: 'flex',
  flexDirection: 'column',
});

// ─── Panel name labels ───

const PANEL_LABELS: Record<PanelId, string> = {
  script: 'Script',
  dag_project: 'DAG Project',
  program_monitor: 'Program',
  source_monitor: 'Source',
  timeline: 'Timeline',
  story_space_3d: 'Story Space',
  effects: 'Effects',
  inspector: 'Inspector',
};

// ─── Component ───

interface PanelShellProps {
  panelId: PanelId;
  children: ReactNode;
  /** Override title text */
  title?: string;
  /** Hide title bar (for monitors in fullscreen) */
  hideTitleBar?: boolean;
}

export default function PanelShell({ panelId, children, title, hideTitleBar }: PanelShellProps) {
  const panel = usePanelLayoutStore((s) => s.getPanel(panelId));
  const detach = usePanelLayoutStore((s) => s.detach);
  const dock = usePanelLayoutStore((s) => s.dock);
  const togglePanel = usePanelLayoutStore((s) => s.togglePanel);
  const toggleMini = usePanelLayoutStore((s) => s.toggleMini);
  const moveFloating = usePanelLayoutStore((s) => s.moveFloating);

  // Drag state for floating panels
  const dragRef = useRef<{ startX: number; startY: number; origX: number; origY: number } | null>(null);

  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (!panel || panel.mode !== 'floating' || !panel.floatGeometry) return;
      dragRef.current = {
        startX: e.clientX,
        startY: e.clientY,
        origX: panel.floatGeometry.x,
        origY: panel.floatGeometry.y,
      };
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    },
    [panel],
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!dragRef.current) return;
      const dx = e.clientX - dragRef.current.startX;
      const dy = e.clientY - dragRef.current.startY;
      moveFloating(panelId, dragRef.current.origX + dx, dragRef.current.origY + dy);
    },
    [panelId, moveFloating],
  );

  const handlePointerUp = useCallback(() => {
    dragRef.current = null;
  }, []);

  if (!panel || !panel.visible) return null;

  const label = title || PANEL_LABELS[panelId] || panelId;

  // ─── Mini mode (floating inside parent) ───
  if (panel.isMini && panel.floatGeometry) {
    const g = panel.floatGeometry;
    return (
      <div style={miniStyle(g.x, g.y, g.width, g.height)}>
        <div
          style={{ ...TITLE_BAR, height: 18, padding: '0 4px' }}
        >
          <span style={{ ...TITLE_TEXT, fontSize: 9 }}>{label}</span>
          <div style={TITLE_ACTIONS}>
            <button
              style={ACTION_BTN}
              onClick={() => toggleMini(panelId)}
              title="Expand"
            >
              <IconExpand size={10} />
            </button>
          </div>
        </div>
        <div style={CONTENT}>{children}</div>
      </div>
    );
  }

  // ─── Floating mode ───
  if (panel.mode === 'floating' && panel.floatGeometry) {
    const g = panel.floatGeometry;
    return (
      <div style={floatingStyle(g.x, g.y, g.width, g.height)}>
        <div
          style={FLOATING_TITLE_BAR}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
        >
          <span style={TITLE_TEXT}>{label}</span>
          <div style={TITLE_ACTIONS}>
            {panel.miniParentId && (
              <button style={ACTION_BTN} onClick={() => toggleMini(panelId)} title="Mini">
                <IconCollapse size={12} />
              </button>
            )}
            <button
              style={ACTION_BTN}
              onClick={() => dock(panelId, 'left')}
              title="Dock"
            >
              <IconDock size={12} />
            </button>
            <button style={ACTION_BTN} onClick={() => togglePanel(panelId)} title="Close">
              <IconClose size={12} />
            </button>
          </div>
        </div>
        <div style={CONTENT}>{children}</div>
      </div>
    );
  }

  // ─── Docked / Tab mode ───
  return (
    <div style={SHELL_DOCKED}>
      {!hideTitleBar && (
        <div style={TITLE_BAR}>
          <span style={TITLE_TEXT}>{label}</span>
          <div style={TITLE_ACTIONS}>
            <button style={ACTION_BTN} onClick={() => detach(panelId)} title="Detach">
              <IconDetach size={12} />
            </button>
            <button style={ACTION_BTN} onClick={() => togglePanel(panelId)} title="Close">
              <IconClose size={12} />
            </button>
          </div>
        </div>
      )}
      <div style={CONTENT}>{children}</div>
    </div>
  );
}
