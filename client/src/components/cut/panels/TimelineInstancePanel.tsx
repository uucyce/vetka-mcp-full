/**
 * MARKER_GAMMA-C12.2: Timeline Instance Panel — list/switch/fork/close timelines.
 *
 * Shows all timeline instances from useCutEditorStore.timelineTabs.
 * Active timeline highlighted. Click to switch. Fork creates new version.
 * Close removes tab (keeps at least 1).
 *
 * DAG-Timeline projection: each timeline = one path through the DAG.
 * This panel is the navigator between those paths.
 */
import { useCallback, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../../store/useCutEditorStore';
import { useDockviewStore } from '../../../store/useDockviewStore';

const PANEL: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  background: '#0a0a0a',
  fontFamily: 'system-ui, -apple-system, sans-serif',
  fontSize: 10,
  color: '#ccc',
  overflow: 'hidden',
};

const TOOLBAR: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 4,
  padding: '4px 8px',
  borderBottom: '1px solid #1a1a1a',
  flexShrink: 0,
};

const BTN: CSSProperties = {
  background: '#111',
  border: '1px solid #333',
  borderRadius: 3,
  color: '#888',
  fontSize: 9,
  padding: '2px 8px',
  cursor: 'pointer',
};

const MODE_BADGE: Record<string, string> = {
  manual: '#888',
  favorites: '#999',
  script: '#777',
  music: '#aaa',
};

export default function TimelineInstancePanel() {
  const timelineTabs = useCutEditorStore((s) => s.timelineTabs);
  const activeIndex = useCutEditorStore((s) => s.activeTimelineTabIndex);
  const timelineId = useCutEditorStore((s) => s.timelineId);
  const setActiveTab = useCutEditorStore((s) => s.setActiveTimelineTab);
  const removeTab = useCutEditorStore((s) => s.removeTimelineTab);
  const createVersioned = useCutEditorStore((s) => s.createVersionedTimeline);
  const projectId = useCutEditorStore((s) => s.projectId);
  const addTimelinePanel = useDockviewStore((s) => s.addTimelinePanel);

  const handleNew = useCallback(() => {
    const name = projectId || 'untitled';
    const newId = createVersioned(name, 'manual');
    if (newId) {
      const tab = useCutEditorStore.getState().timelineTabs.find((t) => t.id === newId);
      addTimelinePanel(newId, tab?.label || newId);
    }
  }, [projectId, createVersioned, addTimelinePanel]);

  const handleFork = useCallback((sourceId: string) => {
    const name = projectId || 'untitled';
    const newId = createVersioned(name, 'manual');
    // Fork = create new + copy lanes from source (simplified — full fork needs Alpha)
    if (newId) {
      const tab = useCutEditorStore.getState().timelineTabs.find((t) => t.id === newId);
      addTimelinePanel(newId, tab?.label || newId);
    }
  }, [projectId, createVersioned, addTimelinePanel]);

  const handleOpenSideBySide = useCallback((tlId: string, label: string) => {
    addTimelinePanel(tlId, label);
  }, [addTimelinePanel]);

  return (
    <div style={PANEL} data-testid="timeline-instance-panel">
      <div style={TOOLBAR}>
        <span style={{ fontSize: 10, fontWeight: 600, color: '#aaa', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Timelines
        </span>
        <span style={{ flex: 1 }} />
        <button style={BTN} onClick={handleNew} title="New Sequence (⌘N)">+ New</button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto' }}>
        {timelineTabs.map((tab, idx) => {
          const isActive = tab.id === timelineId;
          return (
            <div
              key={tab.id}
              onClick={() => setActiveTab(idx)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '6px 8px',
                borderBottom: '1px solid #111',
                background: isActive ? '#1a1a1a' : 'transparent',
                cursor: 'pointer',
              }}
              onMouseEnter={(e) => { if (!isActive) (e.currentTarget as HTMLElement).style.background = '#141414'; }}
              onMouseLeave={(e) => { if (!isActive) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
            >
              {/* Active indicator */}
              <div style={{
                width: 4, height: 4, borderRadius: '50%',
                background: isActive ? '#ccc' : 'transparent',
                flexShrink: 0,
              }} />

              {/* Label + mode */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  color: isActive ? '#eee' : '#888',
                  fontWeight: isActive ? 600 : 400,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}>
                  {tab.label || tab.id}
                </div>
                <div style={{ fontSize: 8, color: '#555', marginTop: 1 }}>
                  <span style={{ color: MODE_BADGE[tab.mode] || '#666' }}>{tab.mode}</span>
                  {' · '}v{tab.version}
                </div>
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', gap: 2, flexShrink: 0 }}>
                <button
                  onClick={(e) => { e.stopPropagation(); handleOpenSideBySide(tab.id, tab.label || tab.id); }}
                  style={{ ...BTN, padding: '1px 4px', fontSize: 8 }}
                  title="Open in side panel"
                >
                  ⊞
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleFork(tab.id); }}
                  style={{ ...BTN, padding: '1px 4px', fontSize: 8 }}
                  title="Fork timeline"
                >
                  ⑂
                </button>
                {timelineTabs.length > 1 && (
                  <button
                    onClick={(e) => { e.stopPropagation(); removeTab(idx); }}
                    style={{ ...BTN, padding: '1px 4px', fontSize: 8, color: '#555' }}
                    title="Close timeline"
                  >
                    ×
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer: count */}
      <div style={{ padding: '3px 8px', borderTop: '1px solid #1a1a1a', fontSize: 8, color: '#555' }}>
        {timelineTabs.length} timeline{timelineTabs.length !== 1 ? 's' : ''} · DAG projections
      </div>
    </div>
  );
}
