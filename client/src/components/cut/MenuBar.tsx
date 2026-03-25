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
import { PRESET_BUILDERS } from './presetBuilders';
import { API_BASE } from '../../config/api.config';
import {
  type HotkeyPresetName,
  loadPresetName,
  savePresetName,
} from '../../hooks/useCutHotkeys';

const HotkeyEditor = lazy(() => import('./HotkeyEditor'));
// SpeedControl removed — rendered in CutEditorLayoutV2 via store.showSpeedControl
// MARKER_GAMMA-25: WorkspacePresets removed from menubar — switching via Window menu only

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
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            {item.shortcut && <span style={SHORTCUT}>{item.shortcut}</span>}
            <span style={SUBMENU_ARROW}>{'>'}</span>
          </span>
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
      title={item.shortcut ? `${item.label}  (${item.shortcut})` : item.label}
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
        { label: 'New Project...', shortcut: '⌥⌘N', disabled: true },
        { label: 'New Sequence', shortcut: '⌘N', action: () => {
          const s = store.getState();
          const name = s.projectId || 'untitled';
          const newId = s.createVersionedTimeline(name, 'manual');
          // MARKER_GAMMA-C12.1: Open new timeline as dockview panel
          if (newId) {
            const tab = s.timelineTabs.find((t: { id: string }) => t.id === newId);
            dockStore.getState().addTimelinePanel(newId, tab?.label || `Cut ${newId}`);
          }
        }},
        { label: 'Open Project...', shortcut: '⌘O', disabled: true },
        { label: 'Recent Projects', submenu: [
          { label: '(no recent projects)', disabled: true },
        ]},
        { separator: true },
        { label: 'Close Tab', shortcut: '⌘W', action: () => {
          const s = store.getState();
          if (s.timelineTabs.length > 1) {
            s.removeTimelineTab(s.activeTimelineTabIndex);
          }
        }},
        { separator: true },
        { label: 'Save', shortcut: '⌘S', action: () => store.getState().refreshProjectState?.() },
        { label: 'Save As...', shortcut: '⌘⇧S', disabled: true },
        { label: 'Save All', disabled: true },
        { label: 'Revert', action: () => {
          const s = store.getState();
          if (s.refreshProjectState) { void s.refreshProjectState(); }
        }},
        { separator: true },
        { label: 'Import Media...', shortcut: '⌘I', action: () => {
          window.dispatchEvent(new CustomEvent('cut:import-media'));
        }},
        { separator: true },
        { label: 'Export Media...', shortcut: '⌘M', action: () => store.getState().setShowExportDialog(true) },
        { label: 'Export', submenu: [
          { label: 'Premiere XML', disabled: true },
          { label: 'FCPXML', disabled: true },
          { label: 'EDL', disabled: true },
          { label: 'OTIO', disabled: true },
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
        { label: 'Cut', shortcut: '⌘X', action: () => store.getState().cutClips() },
        { label: 'Copy', shortcut: '⌘C', action: () => store.getState().copyClips() },
        { label: 'Paste', shortcut: '⌘V', action: () => store.getState().pasteClips('overwrite') },
        { label: 'Paste Insert', shortcut: '⌘⇧V', action: () => store.getState().pasteClips('insert') },
        { label: 'Paste Attributes', shortcut: '⌥V', action: () => store.getState().pasteAttributes() },
        { separator: true },
        { label: 'Select All', shortcut: '⌘A', action: () => store.getState().selectAllClips() },
        { label: 'Deselect All', shortcut: 'Esc', action: () => store.getState().clearSelection() },
        { separator: true },
        { label: 'Find...', shortcut: '⌘F', disabled: true },
        { separator: true },
        { label: 'Keyboard Shortcuts', shortcut: '⌘⌥K', submenu: [
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
          { label: 'Marker Overlay', submenu: [
            ...([
              ['favorite', 'Favorites'],
              ['comment', 'Comments'],
              ['cam', 'Camera Marks'],
              ['insight', 'Insights'],
              ['bpm_audio', 'BPM Audio'],
              ['bpm_visual', 'BPM Visual'],
              ['bpm_script', 'BPM Script'],
              ['sync_point', 'Sync Points'],
            ] as const).map(([kind, label]) => ({
              label: `${dockStore.getState().isMarkerKindVisible(kind) ? '\u2713 ' : '  '}${label}`,
              action: () => dockStore.getState().toggleMarkerKind(kind),
            })),
          ]},
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
        { label: 'Add Marker', shortcut: 'M', action: () => {
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
        { label: 'Replace', shortcut: 'F11', disabled: true },
        { label: 'Fit to Fill', shortcut: '⇧F11', disabled: true },
        { label: 'Superimpose', shortcut: 'F12', disabled: true },
        { separator: true },
        { label: 'Speed/Duration...', shortcut: '⌘R', action: () => store.getState().setShowSpeedControl(true) },
        { label: 'Make Subclip', shortcut: '⌘U', disabled: true },
        { label: 'Freeze Frame', shortcut: '⇧N', disabled: true },
        { label: 'Scale to Sequence', action: () => {
          // Scale selected clip resolution to match sequence resolution
          // TODO: requires per-clip transform state
        }, disabled: true },
        { separator: true },
        { label: `${store.getState().selectedClipId ? '' : '  '}Clip Enable`, action: () => {
          // TODO: toggle clip enabled/disabled state
        }, disabled: true },
        { label: `${store.getState().linkedSelection ? '\u2713 ' : '  '}Link/Unlink`, shortcut: '⌘L', action: () => {
          store.getState().toggleLinkedSelection();
        }},
        { label: 'Group', shortcut: '⌘G', disabled: true },
        { separator: true },
        { label: 'Copy Filters', disabled: true },
        { label: 'Paste Filters', disabled: true },
        { label: 'Remove Filters', disabled: true },
        { separator: true },
        { label: 'Composite Mode', submenu: [
          { label: 'Normal', disabled: true },
          { label: 'Add', disabled: true },
          { label: 'Subtract', disabled: true },
          { label: 'Multiply', disabled: true },
          { label: 'Screen', disabled: true },
          { label: 'Overlay', disabled: true },
          { label: 'Difference', disabled: true },
        ]},
      ],
    },
    {
      label: 'Sequence',
      items: [
        { label: 'Render In to Out', shortcut: '⌥R', disabled: true },
        { label: 'Render All', disabled: true },
        { separator: true },
        { label: 'Add Edit', shortcut: '⌘K', action: () => {
          // MARKER_GAMMA-2: Direct store call (was keyboard dispatch)
          // TODO: Replace with store.getState().splitClip() when Alpha adds store action
          const s = store.getState();
          const t = s.currentTime;
          const newLanes = s.lanes.map((lane) => ({
            ...lane,
            clips: lane.clips.flatMap((c) => {
              if (t > c.start_sec && t < c.start_sec + c.duration_sec) {
                const leftDur = t - c.start_sec;
                const rightDur = c.duration_sec - leftDur;
                return [
                  { ...c, duration_sec: leftDur },
                  { ...c, clip_id: c.clip_id + '_split', start_sec: t, duration_sec: rightDur,
                    source_in: (c.source_in ?? 0) + leftDur },
                ];
              }
              return [c];
            }),
          }));
          s.setLanes(newLanes);
        }},
        { label: 'Add Edit to All Tracks', shortcut: '⌘⇧K', action: () => {
          // MARKER_GAMMA-2: Split on ALL tracks at playhead
          const s = store.getState();
          const t = s.currentTime;
          const newLanes = s.lanes.map((lane) => ({
            ...lane,
            clips: lane.clips.flatMap((c) => {
              if (t > c.start_sec && t < c.start_sec + c.duration_sec) {
                const leftDur = t - c.start_sec;
                const rightDur = c.duration_sec - leftDur;
                return [
                  { ...c, duration_sec: leftDur },
                  { ...c, clip_id: c.clip_id + '_split', start_sec: t, duration_sec: rightDur,
                    source_in: (c.source_in ?? 0) + leftDur },
                ];
              }
              return [c];
            }),
          }));
          s.setLanes(newLanes);
        }},
        { separator: true },
        { label: 'Lift', shortcut: ';', action: () => store.getState().liftClip() },
        { label: 'Extract', shortcut: "'", action: () => store.getState().extractClip() },
        { separator: true },
        { label: 'Ripple Delete', shortcut: '⌥⌫', action: () => {
          // MARKER_GAMMA-2: Direct store call (was keyboard dispatch)
          // TODO: Replace with store.getState().rippleDelete() when Alpha adds store action
          const s = store.getState();
          if (!s.selectedClipId) return;
          let clipStart = 0;
          let clipDur = 0;
          let clipLaneId = '';
          for (const lane of s.lanes) {
            const clip = lane.clips.find((c) => c.clip_id === s.selectedClipId);
            if (clip) { clipStart = clip.start_sec; clipDur = clip.duration_sec; clipLaneId = lane.lane_id; break; }
          }
          if (!clipLaneId) return;
          const newLanes = s.lanes.map((lane) => {
            if (lane.lane_id !== clipLaneId) return lane;
            return {
              ...lane,
              clips: lane.clips
                .filter((c) => c.clip_id !== s.selectedClipId)
                .map((c) => c.start_sec > clipStart ? { ...c, start_sec: Math.max(0, c.start_sec - clipDur) } : c),
            };
          });
          s.setLanes(newLanes);
          s.setSelectedClip(null);
        }},
        { label: 'Close Gap', action: () => store.getState().closeGap() },
        { label: 'Extend Edit', shortcut: 'E', action: () => store.getState().extendEdit() },
        { separator: true },
        { label: 'Trim Edit', shortcut: 'T', disabled: true },
        { separator: true },
        { label: 'Add Video Transition', shortcut: '⌘T', action: () => store.getState().addDefaultTransition() },
        { label: 'Add Audio Transition', shortcut: '⌘⇧T', action: () => store.getState().addDefaultTransition() },
        { label: 'Transition Alignment', submenu: [
          { label: 'Center on Edit', disabled: true },
          { label: 'Start on Edit', disabled: true },
          { label: 'End on Edit', disabled: true },
        ]},
        { separator: true },
        { label: `${store.getState().snapEnabled ? '\u2713 ' : ''}Snap in Timeline`, shortcut: 'S', action: () => store.getState().toggleSnap() },
        { separator: true },
        { label: 'Insert Tracks...', disabled: true },
        { label: 'Delete Tracks...', disabled: true },
        { separator: true },
        { label: 'Nest Item(s)', disabled: true },
        { label: 'Solo Selected Item(s)', disabled: true },
        { separator: true },
        { label: 'Scene Detection', shortcut: '⌘D', action: () => {
          // MARKER_GAMMA-2: Direct backend call (was keyboard dispatch)
          // TODO: Replace with store.getState().runSceneDetection() when Alpha adds store action
          const s = store.getState();
          if (!s.sandboxRoot || !s.projectId) return;
          void (async () => {
            await fetch(`${API_BASE}/cut/scene-detect-and-apply`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                sandbox_root: s.sandboxRoot, project_id: s.projectId, timeline_id: s.timelineId || 'main',
              }),
            });
            await s.refreshProjectState?.();
          })();
        }},
      ],
    },
    {
      label: 'Window',
      items: [
        { label: 'Workspaces', submenu: [
          { label: 'Editing', shortcut: '⌥⇧1', action: () => switchWorkspace('editing') },
          { label: 'Color', shortcut: '⌥⇧2', action: () => switchWorkspace('color') },
          { label: 'Audio', shortcut: '⌥⇧3', action: () => switchWorkspace('audio') },
          { label: 'Multicam', shortcut: '⌥⇧4', action: () => switchWorkspace('multicam') },
          { label: 'Custom', shortcut: '⌥⇧5', action: () => switchWorkspace('custom') },
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
            // MARKER_GAMMA-R2: API-based reset instead of page reload
            try {
              localStorage.removeItem('cut_dockview_editing');
              localStorage.removeItem('cut_dockview_color');
              localStorage.removeItem('cut_dockview_audio');
              localStorage.removeItem('cut_dockview_custom');
              localStorage.removeItem('cut_dockview_active');
              localStorage.removeItem('cut_focus_per_preset');
            } catch {}
            const api = dockStore.getState().apiRef;
            if (api) {
              try {
                api.clear();
                const builder = PRESET_BUILDERS.editing;
                builder(api, '');
                dockStore.getState().setActivePreset('editing');
                requestAnimationFrame(() => {
                  try { dockStore.getState().saveLayout('editing', api.toJSON()); } catch {}
                });
              } catch { /* fallback: reload if API reset fails */
                window.location.reload();
              }
            } else {
              window.location.reload();
            }
          }},
        ]},
        { separator: true },
        { label: 'Project Panel', shortcut: '⇧1', action: () => togglePanel('project', 'project', 'Project') },
        { label: 'Source Monitor', shortcut: '⇧2', action: () => togglePanel('source', 'source', 'SOURCE') },
        { label: 'Timeline', shortcut: '⇧3', action: () => togglePanel('timeline', 'timeline', 'Timeline') },
        { label: 'Program Monitor', shortcut: '⇧4', action: () => togglePanel('program', 'program', 'PROGRAM') },
        { separator: true },
        { label: 'Inspector', shortcut: '⇧5', action: () => togglePanel('inspector', 'inspector', 'Inspector') },
        { label: 'Clip Inspector', action: () => togglePanel('clip', 'clip', 'Clip') },
        { label: 'StorySpace 3D', action: () => togglePanel('storyspace', 'storyspace', 'StorySpace') },
        { label: 'History', action: () => togglePanel('history', 'history', 'History') },
        { separator: true },
        { label: 'Tools', action: () => togglePanel('tools', 'tools', 'Tools') },
        { label: 'Audio Mixer', action: () => togglePanel('mixer', 'mixer', 'Mixer') },
        { label: 'Effects', action: () => togglePanel('effects', 'effects', 'Effects') },
        { label: 'Video Scopes', action: () => togglePanel('scopes', 'scopes', 'Scopes') },
        { label: 'Color Corrector', action: () => togglePanel('colorcorrector', 'colorcorrector', 'Color') },
        { label: 'LUT Browser', action: () => togglePanel('lutbrowser', 'lutbrowser', 'LUTs') },
        { separator: true },
        // Speed Control removed from panels — it's a modal dialog (Clip → Speed/Duration ⌘R)
        // Transitions removed from panels — it's a category inside Effects (GAMMA-LAYOUT1)
        { label: 'Montage', action: () => togglePanel('montage', 'montage', 'Montage') },
        { label: 'Marker List', action: () => togglePanel('markers', 'markers', 'Markers') },
        { label: 'Timeline Navigator', action: () => togglePanel('timelines', 'timelines', 'Timelines') },
        { label: 'Publish / Crosspost', action: () => togglePanel('publish', 'publish', 'Publish') },
        { label: 'Script', action: () => togglePanel('script', 'script', 'Script') },
        { label: 'Graph', action: () => togglePanel('graph', 'graph', 'Graph') },
        { separator: true },
        // MARKER_GAMMA-C12.1: Multi-timeline management
        { label: 'Open Timeline Side by Side', action: () => {
          // Open a second timeline panel beside the existing one
          const api = dockStore.getState().apiRef;
          if (!api) return;
          const s = store.getState();
          const tabs = s.timelineTabs || [];
          if (tabs.length < 2) return; // need at least 2 timelines
          // Find a timeline that's not currently the main panel
          const mainTlId = s.timelineId || 'main';
          const other = tabs.find((t: { id: string }) => t.id !== mainTlId);
          if (!other) return;
          const panelId = `timeline-${other.id}`;
          try { if (api.getPanel(panelId)) { api.getPanel(panelId)!.api.setActive(); return; } } catch { /* ok */ }
          const mainPanel = api.getPanel('timeline');
          api.addPanel({
            id: panelId,
            component: 'timeline',
            title: other.label || other.id,
            params: { timelineId: other.id },
            position: mainPanel
              ? { referencePanel: mainPanel.id, direction: 'right' }
              : { direction: 'below' },
          });
        }},
        { label: 'Timelines', submenu: (() => {
          const tabs = store.getState().timelineTabs || [];
          return tabs.map((t: { id: string; label: string }) => ({
            label: `${store.getState().timelineId === t.id ? '\u2713 ' : '  '}${t.label || t.id}`,
            action: () => {
              const s = store.getState();
              const idx = s.timelineTabs.findIndex((tab: { id: string }) => tab.id === t.id);
              if (idx >= 0) s.setActiveTimelineTab(idx);
            },
          }));
        })() },
        { separator: true },
        { label: 'Maximize Panel', shortcut: '`', action: () => dockStore.getState().toggleMaximize() },
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
    // MARKER_GAMMA-12: Save current focus before switching
    const currentFocus = store.getState().focusedPanel;
    ds.saveFocusForPreset(ds.activePreset, currentFocus);
    // Save current layout before switching
    try { ds.saveLayout(ds.activePreset, api.toJSON()); } catch {}
    // Load target preset
    const saved = ds.loadLayout(name);
    if (saved) {
      try { api.fromJSON(saved); } catch {}
      ds.setActivePreset(name);
      // MARKER_GAMMA-12: Restore focus for target preset
      const targetFocus = ds.getFocusForPreset(name);
      if (targetFocus) {
        store.getState().setFocusedPanel(targetFocus as any);
      }
    } else {
      // MARKER_GAMMA-28: No saved layout — build via API instead of reload
      ds.setActivePreset(name);
      try {
        api.clear();
        const builder = PRESET_BUILDERS[name] || PRESET_BUILDERS.editing;
        builder(api, '');
        requestAnimationFrame(() => {
          try { ds.saveLayout(name, api.toJSON()); } catch { /* ok */ }
        });
      } catch { /* builder failed — layout will rebuild on next mount */ }
    }
  }

  function focusPanel(panelId: string) {
    const api = dockStore.getState().apiRef;
    if (!api) return;
    try {
      const panel = api.getPanel(panelId);
      if (panel) panel.api.setActive();
    } catch {}
  }

  // MARKER_PANEL-TOGGLE: Toggle panel — reopen if closed
  function togglePanel(id: string, component: string, title: string) {
    dockStore.getState().togglePanel(id, component, title);
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
        {/* MARKER_GAMMA-25: Workspace switching via Window menu only (FCP7 style) */}
        <div style={{ flex: 1 }} />
      </div>
      {hotkeyEditorOpen && (
        <Suspense fallback={null}>
          <HotkeyEditor onClose={() => setHotkeyEditorOpen(false)} />
        </Suspense>
      )}
    </>
  );
}
