/**
 * MARKER_GAMMA-CLIP1: Right-click context menu for timeline clips.
 *
 * Standalone component — Alpha wires onContextMenu in TimelineTrackView.
 *
 * FCP7/Premiere convention: right-click on clip shows editing actions.
 * All actions dispatch to useCutEditorStore — no direct timeline mutation.
 *
 * Integration:
 *   import ClipContextMenu from './ClipContextMenu';
 *   <ClipContextMenu
 *     clipId={rightClickedClipId}
 *     position={{ x: event.clientX, y: event.clientY }}
 *     onClose={() => setContextMenu(null)}
 *   />
 */
import { useCallback, useEffect, useRef, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';

// ─── Types ───

export interface ClipContextMenuProps {
  clipId: string;
  position: { x: number; y: number };
  onClose: () => void;
}

interface MenuItem {
  label: string;
  shortcut?: string;
  action: () => void;
  separator?: false;
  disabled?: boolean;
}

interface MenuSeparator {
  separator: true;
}

type MenuEntry = MenuItem | MenuSeparator;

// ─── Styles (monochrome, FCP7) ───

const MENU_STYLE: CSSProperties = {
  position: 'fixed',
  zIndex: 9999,
  background: '#1a1a1a',
  border: '1px solid #333',
  borderRadius: 4,
  padding: '4px 0',
  minWidth: 200,
  boxShadow: '0 4px 16px rgba(0,0,0,0.6)',
  fontFamily: 'system-ui, -apple-system, sans-serif',
  fontSize: 12,
  color: '#ccc',
  userSelect: 'none',
};

const ITEM_STYLE: CSSProperties = {
  padding: '5px 12px 5px 16px',
  cursor: 'pointer',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  whiteSpace: 'nowrap',
};

const ITEM_HOVER: CSSProperties = {
  ...ITEM_STYLE,
  background: '#333',
};

const SHORTCUT_STYLE: CSSProperties = {
  color: '#666',
  fontSize: 11,
  marginLeft: 24,
};

const SEPARATOR_STYLE: CSSProperties = {
  height: 1,
  background: '#333',
  margin: '4px 8px',
};

const DISABLED_STYLE: CSSProperties = {
  ...ITEM_STYLE,
  color: '#555',
  cursor: 'default',
};

// ─── Component ───

export default function ClipContextMenu({ clipId, position, onClose }: ClipContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);
  const hoverIdx = useRef(-1);

  // Close on outside click / Escape
  useEffect(() => {
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
  }, [onClose]);

  // Position adjustment: keep menu within viewport
  useEffect(() => {
    if (!menuRef.current) return;
    const rect = menuRef.current.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    if (rect.right > vw) {
      menuRef.current.style.left = `${vw - rect.width - 8}px`;
    }
    if (rect.bottom > vh) {
      menuRef.current.style.top = `${vh - rect.height - 8}px`;
    }
  }, [position]);

  const store = useCutEditorStore.getState;

  const entries: MenuEntry[] = [
    {
      label: 'Cut',
      shortcut: '\u2318X',
      action: () => { store().cutClips(); onClose(); },
    },
    {
      label: 'Copy',
      shortcut: '\u2318C',
      action: () => { store().copyClips(); onClose(); },
    },
    {
      label: 'Paste',
      shortcut: '\u2318V',
      action: () => { store().pasteClips('overwrite'); onClose(); },
    },
    { separator: true },
    {
      label: 'Delete',
      shortcut: 'Del',
      action: async () => {
        await store().applyTimelineOps([{ op: 'remove_clip', clip_id: clipId }]);
        store().setSelectedClip(null);
        onClose();
      },
    },
    {
      label: 'Ripple Delete',
      shortcut: '\u21E7Del',
      action: async () => {
        await store().applyTimelineOps([{ op: 'ripple_delete', clip_id: clipId }]);
        store().setSelectedClip(null);
        onClose();
      },
    },
    { separator: true },
    {
      label: 'Speed / Duration\u2026',
      shortcut: '\u2318R',
      action: () => {
        // Dispatch custom event to open SpeedControl modal
        window.dispatchEvent(new CustomEvent('cut:open-speed-dialog', { detail: { clipId } }));
        onClose();
      },
    },
    { separator: true },
    {
      label: 'Properties',
      action: () => {
        store().setSelectedClip(clipId);
        store().setFocusedPanel('effects');
        onClose();
      },
    },
    {
      label: 'Reveal in Project',
      action: () => {
        // Find clip source path and highlight in project panel
        const s = store();
        for (const lane of s.lanes) {
          for (const clip of lane.clips || []) {
            if (clip.clip_id === clipId && clip.source_path) {
              window.dispatchEvent(new CustomEvent('cut:reveal-in-project', {
                detail: { sourcePath: clip.source_path },
              }));
              break;
            }
          }
        }
        onClose();
      },
    },
  ];

  const handleItemClick = useCallback((entry: MenuEntry) => {
    if ('separator' in entry && entry.separator) return;
    if (entry.disabled) return;
    entry.action();
  }, []);

  return (
    <div
      ref={menuRef}
      style={{ ...MENU_STYLE, left: position.x, top: position.y }}
      data-testid="clip-context-menu"
    >
      {entries.map((entry, i) => {
        if ('separator' in entry && entry.separator) {
          return <div key={i} style={SEPARATOR_STYLE} />;
        }
        return (
          <div
            key={i}
            style={entry.disabled ? DISABLED_STYLE : ITEM_STYLE}
            onClick={() => handleItemClick(entry)}
            onMouseEnter={(e) => {
              if (!entry.disabled) {
                (e.currentTarget as HTMLElement).style.background = '#333';
              }
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.background = 'transparent';
            }}
          >
            <span>{entry.label}</span>
            {entry.shortcut && <span style={SHORTCUT_STYLE}>{entry.shortcut}</span>}
          </div>
        );
      })}
    </div>
  );
}
