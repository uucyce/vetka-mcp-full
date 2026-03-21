/**
 * MARKER_LAYOUT-1: MenuBar — NLE standard menu bar (File/Edit/View/Mark/Clip/Sequence/Window/Help).
 *
 * Every professional NLE (Premiere, FCP7, DaVinci, Avid) has a menu bar.
 * CUT now has one too.
 *
 * Design: 22px height, #0a0a0a bg, #ccc text, monospace-ish.
 * Menus open on click, close on Esc / outside click.
 * Shortcut labels right-aligned in each row.
 *
 * @phase 199
 */
import { useState, useCallback, useEffect, useRef, lazy, Suspense, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { useDockviewStore, type WorkspacePresetName } from '../../store/useDockviewStore';
import {
  type HotkeyPresetName,
  loadPresetName,
  savePresetName,
} from '../../hooks/useCutHotkeys';

const HotkeyEditor = lazy(() => import('./HotkeyEditor'));

// ─── Types ─────────────────────────────────────────────────────────

interface MenuItem {
  label?: string;
  shortcut?: string;
  action?: () => void;
  separator?: boolean;
  disabled?: boolean;
  submenu?: MenuItem[];
}

interface MenuDef {
  label: string;
  items: MenuItem[];
}

// ─── Styles ────────────────────────────────────────────────────────

const BAR: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  height: 22,
  background: '#0a0a0a',
  borderBottom: '1px solid #1a1a1a',
  padding: '0 4px',
  flexShrink: 0,
  userSelect: 'none',
  zIndex: 1000,
};

const MENU_TRIGGER: CSSProperties = {
  padding: '0 8px',
  height: 22,
  lineHeight: '22px',
  fontSize: 11,
  fontFamily: 'system-ui, -apple-system, sans-serif',
  color: '#ccc',
  cursor: 'pointer',
  borderRadius: 2,
  border: 'none',
  background: 'none',
};

const MENU_TRIGGER_ACTIVE: CSSProperties = {
  ...MENU_TRIGGER,
  background: '#222',
  color: '#fff',
};

const DROPDOWN: CSSProperties = {
  position: 'absolute',
  top: 22,
  left: 0,
  background: '#1a1a1a',
  border: '1px solid #333',
  borderRadius: 4,
  padding: '3px 0',
  minWidth: 220,
  zIndex: 1001,
  boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
};

const ITEM: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '4px 16px 4px 12px',
  fontSize: 11,
  fontFamily: 'system-ui, -apple-system, sans-serif',
  color: '#ccc',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
};

const ITEM_DISABLED: CSSProperties = {
  ...ITEM,
  color: '#555',
  cursor: 'default',
};

const SHORTCUT: CSSProperties = {
  fontSize: 10,
  color: '#666',
  fontFamily: 'monospace',
  marginLeft: 24,
};

const SEPARATOR: CSSProperties = {
  height: 1,
  background: '#333',
  margin: '3px 8px',
};

const SUBMENU_ARROW: CSSProperties = {
  fontSize: 8,
  color: '#555',
  marginLeft: 8,
};

// ─── Menu Item Component ───────────────────────────────────────────

function MenuItemRow({
  item,
  onAction,
}: {
  item: MenuItem;
  onAction: () => void;
}) {
  const [subOpen, setSubOpen] = useState(false);

  if (item.separator) return <div style={SEPARATOR} />;

  if (item.submenu) {
    return (
      <div
        style={{ position: 'relative' }}
        onMouseEnter={() => setSubOpen(true)}
        onMouseLeave={() => setSubOpen(false)}
      >
        <div style={ITEM}>
          <span>{item.label}</span>
          <span style={SUBMENU_ARROW}>{'>'}</span>
        </div>
        {subOpen && (
          <div style={{ ...DROPDOWN, top: -3, left: '100%' }}>
            {item.submenu.map((sub, i) => (
              <MenuItemRow key={i} item={sub} onAction={onAction} />
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      style={item.disabled ? ITEM_DISABLED : ITEM}
      onMouseEnter={(e) => {
        if (!item.disabled) (e.currentTarget as HTMLDivElement).style.background = '#333';
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLDivElement).style.background = 'transparent';
      }}
      onClick={() => {
        if (item.disabled) return;
        item.action?.();
        onAction();
      }}
    >
      <span>{item.label}</span>
      {item.shortcut && <span style={SHORTCUT}>{item.shortcut}</span>}
    </div>
  );
}

// ─── Main Component ────────────────────────────────────────────────

export default function MenuBar() {
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const [hotkeyEditorOpen, setHotkeyEditorOpen] = useState(false);
  const barRef = useRef<HTMLDivElement>(null);

  // Store actions
  const store = useCutEditorStore;
  const dockStore = useDockviewStore;

  // Close on Esc or outside click
  useEffect(() => {
    if (!openMenu) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpenMenu(null);
    };
    const onClick = (e: MouseEvent) => {
      if (barRef.current && !barRef.current.contains(e.target as Node)) {
        setOpenMenu(null);
      }
    };
    window.addEventListener('keydown', onKey);
    window.addEventListener('mousedown', onClick);
    return () => {
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('mousedown', onClick);
    };
  }, [openMenu]);

  const closeMenu = useCallback(() => setOpenMenu(null), []);

  // ─── Menu definitions ────────────────────────────────────────────

  const menus: MenuDef[] = [
    {
      label: 'File',
      items: [
        { label: 'Save', shortcut: '⌘S', action: () => store.getState().refreshProjectState?.() },
        { label: 'Save As...', shortcut: '⌘⇧S', disabled: true },
        { separator: true },
        { label: 'Import Media...', shortcut: '⌘I', action: () => {
          // Trigger import via existing hotkey action
          document.dispatchEvent(new KeyboardEvent('keydown', { key: 'i', metaKey: true }));
        }},
        { separator: true },
        { label: 'Export Media...', shortcut: '⌘M', action: () => store.getState().setShowExportDialog(true) },
        { label: 'Export', submenu: [
          { label: 'Premiere XML', action: () => {}, disabled: true },
          { label: 'FCPXML', action: () => {}, disabled: true },
          { label: 'EDL', action: () => {}, disabled: true },
          { label: 'OTIO', action: () => {}, disabled: true },
        ]},
        { separator: true },
        { label: 'Project Settings...', shortcut: '⌘;', action: () => store.getState().setShowProjectSettings(true) },
      ],
    },
    {
      label: 'Edit',
      items: [
        { label: 'Undo', shortcut: '⌘Z', action: () => {
          document.dispatchEvent(new KeyboardEvent('keydown', { key: 'z', metaKey: true }));
        }},
        { label: 'Redo', shortcut: '⌘⇧Z', action: () => {
          document.dispatchEvent(new KeyboardEvent('keydown', { key: 'z', metaKey: true, shiftKey: true }));
        }},
        { separator: true },
        { label: 'Cut', shortcut: '⌘X', disabled: true },
        { label: 'Copy', shortcut: '⌘C', disabled: true },
        { label: 'Paste', shortcut: '⌘V', disabled: true },
        { separator: true },
        { label: 'Select All', shortcut: '⌘A', action: () => store.getState().selectAllClips() },
        { label: 'Deselect All', shortcut: 'Esc', action: () => store.getState().clearSelection() },
        { separator: true },
        { label: 'Keyboard Shortcuts', submenu: [
          { label: 'Edit Shortcuts...', shortcut: '⌘⌥K', action: () => setHotkeyEditorOpen(true) },
          { separator: true },
          ...(['premiere', 'fcp7', 'custom'] as HotkeyPresetName[]).map((p) => ({
            label: `${loadPresetName() === p ? '\u2713 ' : '  '}${{ premiere: 'Premiere Pro', fcp7: 'Final Cut Pro 7', custom: 'Custom' }[p]}`,
            action: () => {
              savePresetName(p);
              window.dispatchEvent(new StorageEvent('storage', { key: 'cut_hotkey_preset', newValue: p }));
            },
          })),
        ]},
      ],
    },
    {
      label: 'View',
      items: [
        // MARKER_FIX-VIEW-MENU: Context-aware zoom (monitor vs timeline)
        { label: 'Zoom In', shortcut: '=', action: () => {
          const s = store.getState();
          const fp = s.focusedPanel;
          if (fp === 'source' || fp === 'program') {
            const steps = [0, 50, 75, 100, 150, 200];
            const cur = steps.indexOf(s.monitorZoom);
            if (cur < steps.length - 1) s.setMonitorZoom(steps[cur + 1]);
          } else {
            s.setZoom(Math.min(300, s.zoom + 20));
          }
        }},
        { label: 'Zoom Out', shortcut: '-', action: () => {
          const s = store.getState();
          const fp = s.focusedPanel;
          if (fp === 'source' || fp === 'program') {
            const steps = [0, 50, 75, 100, 150, 200];
            const cur = steps.indexOf(s.monitorZoom);
            if (cur > 0) s.setMonitorZoom(steps[cur - 1]);
          } else {
            s.setZoom(Math.max(10, s.zoom - 20));
          }
        }},
        { label: 'Zoom to Fit', shortcut: '\\', action: () => {
          const s = store.getState();
          const fp = s.focusedPanel;
          if (fp === 'source' || fp === 'program') {
            s.setMonitorZoom(0);
          } else if (s.duration > 0) {
            s.setZoom(Math.max(10, Math.min(300, 800 / s.duration)));
            s.setScrollLeft(0);
          }
        }},
        { separator: true },
        { label: `${store.getState().snapEnabled ? '\u2713 ' : ''}Snapping`, shortcut: 'S', action: () => {
          store.getState().toggleSnap();
        }},
        { separator: true },
        { label: 'Monitor Zoom', submenu: [
          ...([0, 50, 75, 100, 150, 200] as const).map((z) => ({
            label: `${store.getState().monitorZoom === z ? '\u2713 ' : '  '}${z === 0 ? 'Fit' : `${z}%`}`,
            action: () => store.getState().setMonitorZoom(z),
          })),
        ]},
        { label: 'Overlays', submenu: [
          { label: `${store.getState().showTitleSafe ? '\u2713 ' : '  '}Title Safe`, action: () => store.getState().toggleTitleSafe() },
          { label: `${store.getState().showActionSafe ? '\u2713 ' : '  '}Action Safe`, action: () => store.getState().toggleActionSafe() },
          { separator: true },
          { label: `${store.getState().showMonitorOverlays ? '\u2713 ' : '  '}Timecode Overlay`, action: () => store.getState().toggleMonitorOverlays() },
          { label: 'Marker Overlay', disabled: true },
        ]},
        { separator: true },
        { label: 'Show Source Monitor', shortcut: '⌘1', action: () => focusPanel('source') },
        { label: 'Show Program Monitor', shortcut: '⌘2', action: () => focusPanel('program') },
        { label: 'Show Timeline', shortcut: '⌘3', action: () => focusPanel('timeline') },
        { label: 'Show Project Panel', shortcut: '⌘4', action: () => focusPanel('project') },
        { label: 'Show Effects Panel', shortcut: '⌘5', action: () => focusPanel('effects') },
        { separator: true },
        { label: 'Toggle NLE / Debug', shortcut: '⌘\\', action: () => {
          const s = store.getState();
          s.setViewMode(s.viewMode === 'nle' ? 'debug' : 'nle');
        }},
      ],
    },
    {
      label: 'Mark',
      items: [
        { label: 'Mark In', shortcut: 'I', action: () => {
          const s = store.getState();
          if (s.focusedPanel === 'source') s.setSourceMarkIn(s.currentTime);
          else s.setSequenceMarkIn(s.currentTime);
        }},
        { label: 'Mark Out', shortcut: 'O', action: () => {
          const s = store.getState();
          if (s.focusedPanel === 'source') s.setSourceMarkOut(s.currentTime);
          else s.setSequenceMarkOut(s.currentTime);
        }},
        { label: 'Mark Clip', shortcut: 'X', action: () => {
          const s = store.getState();
          if (!s.selectedClipId) return;
          for (const lane of s.lanes) {
            const clip = lane.clips.find((c) => c.clip_id === s.selectedClipId);
            if (clip) {
              s.setMarkIn(clip.start_sec);
              s.setMarkOut(clip.start_sec + clip.duration_sec);
              return;
            }
          }
        }},
        { separator: true },
        { label: 'Go to In', shortcut: '⇧I', action: () => {
          const s = store.getState();
          const m = s.focusedPanel === 'source' ? s.sourceMarkIn : s.sequenceMarkIn;
          if (m != null) s.seek(m);
        }},
        { label: 'Go to Out', shortcut: '⇧O', action: () => {
          const s = store.getState();
          const m = s.focusedPanel === 'source' ? s.sourceMarkOut : s.sequenceMarkOut;
          if (m != null) s.seek(m);
        }},
        { separator: true },
        { label: 'Clear In', shortcut: '⌥I', action: () => {
          const s = store.getState();
          if (s.focusedPanel === 'source') s.setSourceMarkIn(null);
          else s.setSequenceMarkIn(null);
        }},
        { label: 'Clear Out', shortcut: '⌥O', action: () => {
          const s = store.getState();
          if (s.focusedPanel === 'source') s.setSourceMarkOut(null);
          else s.setSequenceMarkOut(null);
        }},
        { label: 'Clear In and Out', shortcut: '⌥X', action: () => {
          const s = store.getState();
          if (s.focusedPanel === 'source') { s.setSourceMarkIn(null); s.setSourceMarkOut(null); }
          else { s.setSequenceMarkIn(null); s.setSequenceMarkOut(null); }
        }},
        { separator: true },
        { label: 'Play', submenu: [
          { label: 'Play In to Out', shortcut: '⇧\\', action: () => {
            const s = store.getState();
            const inPt = s.focusedPanel === 'source' ? s.sourceMarkIn : s.sequenceMarkIn;
            const outPt = s.focusedPanel === 'source' ? s.sourceMarkOut : s.sequenceMarkOut;
            if (inPt == null || outPt == null || outPt <= inPt) return;
            s.seek(inPt);
            s.play();
          }},
          { label: 'Play Around Current', shortcut: '\\', action: () => {
            const s = store.getState();
            s.seek(Math.max(0, s.currentTime - 2));
            s.play();
          }},
        ]},
        { separator: true },
        { label: 'Markers', submenu: [
          { label: 'Add Marker', shortcut: 'M', action: () => {
            // Dispatch to hotkey handler (marker creation requires API call context)
            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'm' }));
          }},
          { label: 'Add Comment Marker', shortcut: '⇧M', action: () => {
            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'm', shiftKey: true }));
          }},
          { separator: true },
          { label: 'Next Marker', shortcut: '⇧↓', action: () => {
            const s = store.getState();
            const sorted = [...s.markers].sort((a, b) => a.start_sec - b.start_sec);
            const next = sorted.find((m) => m.start_sec > s.currentTime + 0.001);
            if (next) s.seek(next.start_sec);
          }},
          { label: 'Previous Marker', shortcut: '⇧↑', action: () => {
            const s = store.getState();
            const sorted = [...s.markers].sort((a, b) => b.start_sec - a.start_sec);
            const prev = sorted.find((m) => m.start_sec < s.currentTime - 0.001);
            if (prev) s.seek(prev.start_sec);
          }},
          { separator: true },
          { label: 'Delete Marker', action: () => {
            const s = store.getState();
            const atPlayhead = s.markers.find((m) =>
              s.currentTime >= m.start_sec - 0.05 && s.currentTime <= m.end_sec + 0.05
            );
            if (atPlayhead) {
              s.setMarkers(s.markers.filter((m) => m.marker_id !== atPlayhead.marker_id));
            }
          }},
        ]},
      ],
    },
    {
      label: 'Clip',
      items: [
        { label: 'Insert', shortcut: ',', action: () => {
          document.dispatchEvent(new KeyboardEvent('keydown', { key: ',' }));
        }},
        { label: 'Overwrite', shortcut: '.', action: () => {
          document.dispatchEvent(new KeyboardEvent('keydown', { key: '.' }));
        }},
        { separator: true },
        { label: 'Speed/Duration...', shortcut: '⌘R', disabled: true },
        { label: 'Make Subclip', disabled: true },
        { label: 'Freeze Frame', disabled: true },
        { separator: true },
        { label: 'Link/Unlink', shortcut: '⌘L', action: () => {
          store.getState().toggleLinkedSelection();
        }},
        { label: 'Group', shortcut: '⌘G', disabled: true },
        { separator: true },
        { label: 'Composite Mode', submenu: [
          { label: 'Normal', disabled: true },
          { label: 'Add', disabled: true },
          { label: 'Multiply', disabled: true },
          { label: 'Screen', disabled: true },
          { label: 'Difference', disabled: true },
        ]},
      ],
    },
    {
      label: 'Sequence',
      items: [
        { label: 'Add Edit', shortcut: '⌘K', disabled: true },
        { label: 'Ripple Delete', shortcut: '⌥⌫', disabled: true },
        { separator: true },
        { label: 'Snap in Timeline', shortcut: 'S', action: () => store.getState().toggleSnap() },
        { separator: true },
        { label: 'Scene Detection', shortcut: '⌘D', disabled: true },
      ],
    },
    {
      label: 'Window',
      items: [
        { label: 'Workspaces', submenu: [
          { label: 'Editing', shortcut: '⌥⇧1', action: () => switchWorkspace('editing') },
          { label: 'Color', shortcut: '⌥⇧2', action: () => switchWorkspace('color') },
          { label: 'Audio', shortcut: '⌥⇧3', action: () => switchWorkspace('audio') },
          { label: 'Custom', shortcut: '⌥⇧4', action: () => switchWorkspace('custom') },
          { separator: true },
          { label: 'Save Workspace...', action: () => {
            const api = dockStore.getState().apiRef;
            if (api) {
              const json = api.toJSON();
              dockStore.getState().saveLayout('custom', json);
              dockStore.getState().setActivePreset('custom');
            }
          }},
          { label: 'Reset Workspace', shortcut: '⌥⇧0', action: () => {
            try { localStorage.removeItem('cut_dockview_editing'); } catch {}
            window.location.reload();
          }},
        ]},
        { separator: true },
        { label: 'Project Panel', shortcut: '⇧1', action: () => focusPanel('project') },
        { label: 'Source Monitor', shortcut: '⇧2', action: () => focusPanel('source') },
        { label: 'Timeline', shortcut: '⇧3', action: () => focusPanel('timeline') },
        { label: 'Program Monitor', shortcut: '⇧4', action: () => focusPanel('program') },
        { label: 'Inspector', shortcut: '⇧5', action: () => focusPanel('inspector') },
        { separator: true },
        { label: 'History', action: () => focusPanel('history') },
        { label: 'Audio Mixer', action: () => focusPanel('mixer') },
        { label: 'Effects', action: () => focusPanel('effects') },
        { label: 'Montage', action: () => focusPanel('montage') },
      ],
    },
    {
      label: 'Help',
      items: [
        { label: 'Keyboard Shortcuts Reference', action: () => setHotkeyEditorOpen(true) },
        { separator: true },
        { label: 'About CUT', disabled: true },
      ],
    },
  ];

  function switchWorkspace(name: WorkspacePresetName) {
    const ds = dockStore.getState();
    const api = ds.apiRef;
    if (!api) return;
    // Save current first
    try { ds.saveLayout(ds.activePreset, api.toJSON()); } catch {}
    // Load target
    const saved = ds.loadLayout(name);
    if (saved) {
      try { api.fromJSON(saved); } catch {}
    }
    ds.setActivePreset(name);
  }

  function focusPanel(panelId: string) {
    const api = dockStore.getState().apiRef;
    if (!api) return;
    try {
      const panel = api.getPanel(panelId);
      if (panel) panel.api.setActive();
    } catch {}
  }

  return (
    <>
      <div ref={barRef} style={BAR}>
        {menus.map((menu) => (
          <div key={menu.label} style={{ position: 'relative' }}>
            <button
              style={openMenu === menu.label ? MENU_TRIGGER_ACTIVE : MENU_TRIGGER}
              onClick={() => setOpenMenu(openMenu === menu.label ? null : menu.label)}
              onMouseEnter={() => {
                if (openMenu && openMenu !== menu.label) setOpenMenu(menu.label);
              }}
            >
              {menu.label}
            </button>
            {openMenu === menu.label && (
              <div style={DROPDOWN}>
                {menu.items.map((item, i) => (
                  <MenuItemRow key={i} item={item} onAction={closeMenu} />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      {hotkeyEditorOpen && (
        <Suspense fallback={null}>
          <HotkeyEditor onClose={() => setHotkeyEditorOpen(false)} />
        </Suspense>
      )}
    </>
  );
}
