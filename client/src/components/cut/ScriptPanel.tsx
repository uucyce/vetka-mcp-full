/**
 * MARKER_180.5: ScriptPanel — the spine of VETKA CUT.
 * Vertical Y-time panel. Lines with timecodes.
 * Click line → sync playhead + DAG + source monitor.
 * Auto-scroll on playback (teleprompter mode).
 *
 * Architecture doc §2.1:
 * - Axis: Y = time (vertical, chat-like). 1 line ≈ 1 minute
 * - Click line → source monitor shows linked material
 * - Play button scrolls text like teleprompter
 * - BPM display: three colored dots (audio/visual/script)
 *
 * Architecture doc §4: "Script uses Y-time (vertical) because project
 * panels are typically narrow and tall."
 */
import { useCallback, useEffect, useRef, useState, type CSSProperties } from 'react';
import { usePanelSyncStore } from '../../store/usePanelSyncStore';
import { useCutEditorStore } from '../../store/useCutEditorStore';

// ─── Types ───

interface ScriptLine {
  index: number;
  text: string;
  timecode: string;       // "00:00", "01:30", etc.
  time_sec: number;
  scene_id: string;
  type: 'scene_header' | 'action' | 'dialogue' | 'transition' | 'empty';
}

// ─── Styles (§11 compliant) ───

const PANEL: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  width: '100%',
  height: '100%',
  background: '#1A1A1A',
  overflow: 'hidden',
};

const TAB_BAR: CSSProperties = {
  display: 'flex',
  gap: 1,
  padding: '0 4px',
  background: '#141414',
  borderBottom: '0.5px solid #333',
  flexShrink: 0,
};

const TAB: CSSProperties = {
  padding: '4px 10px',
  fontSize: 10,
  fontFamily: 'Inter, system-ui, sans-serif',
  background: '#1A1A1A',
  color: '#555',
  border: 'none',
  borderRadius: '2px 2px 0 0',
  cursor: 'pointer',
  transition: 'color 0.15s, background 0.15s',
};

const TAB_ACTIVE: CSSProperties = {
  ...TAB,
  background: '#252525',
  color: '#E0E0E0',
  fontWeight: 500,
};

const SCRIPT_LIST: CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  padding: '4px 0',
};

const LINE_BASE: CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  padding: '4px 8px',
  borderLeft: '2px solid transparent',
  fontSize: 11,
  fontFamily: 'Inter, system-ui, sans-serif',
  lineHeight: 1.6,
  color: '#888',
  cursor: 'pointer',
  borderRadius: '0 4px 4px 0',
  transition: 'all 0.12s',
};

const LINE_ACTIVE: CSSProperties = {
  ...LINE_BASE,
  borderLeftColor: '#4a9eff',
  background: 'rgba(74, 158, 255, 0.08)',
  color: '#E0E0E0',
};

const LINE_HOVER: CSSProperties = {
  background: '#252525',
};

const TIMECODE: CSSProperties = {
  fontSize: 9,
  fontFamily: '"JetBrains Mono", monospace',
  color: '#555',
  marginRight: 8,
  minWidth: 36,
  flexShrink: 0,
  userSelect: 'none',
};

const SCENE_HEADER: CSSProperties = {
  fontWeight: 600,
  color: '#E0E0E0',
  textTransform: 'uppercase',
  fontSize: 10,
  letterSpacing: '0.5px',
};

// ─── BPM Display (§5.1) ───

const BPM_CONTAINER: CSSProperties = {
  display: 'flex',
  gap: 10,
  padding: '6px 8px',
  borderTop: '0.5px solid #333',
  background: '#141414',
  flexShrink: 0,
  fontSize: 10,
  color: '#555',
  fontFamily: 'Inter, system-ui, sans-serif',
};

const BPM_DOT = (color: string): CSSProperties => ({
  width: 6,
  height: 6,
  borderRadius: '50%',
  background: color,
  display: 'inline-block',
  marginRight: 4,
  verticalAlign: 'middle',
});

// ─── Helper: format seconds to MM:SS ───

function formatTime(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

// ─── Helper: parse script text into lines ───

function parseScript(text: string): ScriptLine[] {
  if (!text.trim()) return [];

  const rawLines = text.split('\n');
  const result: ScriptLine[] = [];
  let currentScene = 'sc_0';
  let sceneIdx = 0;

  for (let i = 0; i < rawLines.length; i++) {
    const line = rawLines[i].trim();
    if (!line) continue;

    // Detect line type
    let type: ScriptLine['type'] = 'action';
    if (/^(INT\.|EXT\.|INT\/EXT\.)/.test(line)) {
      type = 'scene_header';
      sceneIdx++;
      currentScene = `sc_${sceneIdx}`;
    } else if (/^(CUT TO|FADE|DISSOLVE|SMASH CUT)/.test(line)) {
      type = 'transition';
    } else if (/^[A-Z]{2,}(\s*\(.*\))?\s*$/.test(line)) {
      // Character name (all caps) — next line is dialogue
      type = 'dialogue';
    } else if (line.startsWith('"') || line.startsWith("'")) {
      type = 'dialogue';
    }

    // Approximate time: 1 line ≈ 4 seconds (55 lines per page, 1 page ≈ 60 sec)
    const timeSec = result.length * 4;

    result.push({
      index: result.length,
      text: line,
      timecode: formatTime(timeSec),
      time_sec: timeSec,
      scene_id: currentScene,
      type,
    });
  }

  return result;
}

// ─── Component ───

interface ScriptPanelProps {
  /** Script text (screenplay or auto-transcript) */
  scriptText?: string;
  /** Active tab override */
  activeTab?: 'script' | 'dag';
  /** Callback when tab changes */
  onTabChange?: (tab: 'script' | 'dag') => void;
}

export default function ScriptPanel({ scriptText = '', activeTab: tabProp, onTabChange }: ScriptPanelProps) {
  const [tab, setTab] = useState<'script' | 'dag'>(tabProp || 'script');
  const [hoveredLine, setHoveredLine] = useState<number | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Sync store
  const syncFromScript = usePanelSyncStore((s) => s.syncFromScript);
  const selectedScriptLine = usePanelSyncStore((s) => s.selectedScriptLine);
  const playheadSec = usePanelSyncStore((s) => s.playheadSec);
  const lastSyncSource = usePanelSyncStore((s) => s.lastSyncSource);
  const audioBPM = usePanelSyncStore((s) => s.currentAudioBPM);
  const visualBPM = usePanelSyncStore((s) => s.currentVisualBPM);
  const scriptBPM = usePanelSyncStore((s) => s.currentScriptBPM);

  // Editor store (for isPlaying teleprompter)
  const isPlaying = useCutEditorStore((s) => s.isPlaying);

  const lines = parseScript(scriptText);

  // ─── Click line → sync ───
  const handleLineClick = useCallback(
    (line: ScriptLine) => {
      syncFromScript(line.index, line.scene_id, line.time_sec);
    },
    [syncFromScript],
  );

  // ─── Teleprompter auto-scroll during playback ───
  useEffect(() => {
    if (!isPlaying || !listRef.current || lastSyncSource === 'script') return;

    // Find the line closest to current playhead
    const targetLine = lines.findIndex((l) => l.time_sec >= playheadSec);
    if (targetLine < 0) return;

    const lineEl = listRef.current.children[targetLine] as HTMLElement | undefined;
    if (lineEl) {
      lineEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [playheadSec, isPlaying, lines, lastSyncSource]);

  // ─── Tab handling ───
  const handleTabChange = useCallback(
    (newTab: 'script' | 'dag') => {
      setTab(newTab);
      onTabChange?.(newTab);
    },
    [onTabChange],
  );

  return (
    <div style={PANEL}>
      {/* Tab bar: Script / DAG project (§2.1) */}
      <div style={TAB_BAR}>
        <button
          style={tab === 'script' ? TAB_ACTIVE : TAB}
          onClick={() => handleTabChange('script')}
        >
          Script
        </button>
        <button
          style={tab === 'dag' ? TAB_ACTIVE : TAB}
          onClick={() => handleTabChange('dag')}
        >
          DAG project
        </button>
      </div>

      {/* Script lines */}
      {tab === 'script' && (
        <div ref={listRef} style={SCRIPT_LIST}>
          {lines.length === 0 && (
            <div style={{ padding: 16, color: '#555', fontSize: 11, textAlign: 'center' }}>
              No script loaded. Import media → auto-transcribe → becomes script.
            </div>
          )}
          {lines.map((line) => {
            const isActive = selectedScriptLine === line.index;
            const isHovered = hoveredLine === line.index;

            return (
              <div
                key={line.index}
                style={{
                  ...(isActive ? LINE_ACTIVE : LINE_BASE),
                  ...(isHovered && !isActive ? LINE_HOVER : {}),
                }}
                onClick={() => handleLineClick(line)}
                onMouseEnter={() => setHoveredLine(line.index)}
                onMouseLeave={() => setHoveredLine(null)}
              >
                <span style={TIMECODE}>{line.timecode}</span>
                <span style={line.type === 'scene_header' ? SCENE_HEADER : undefined}>
                  {line.text}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* DAG project tab — placeholder, rendered by DAGProjectPanel */}
      {tab === 'dag' && (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#555', fontSize: 11 }}>
          DAG Project panel (180.16)
        </div>
      )}

      {/* BPM display (§5.1, MARKER_180.6) */}
      <div style={BPM_CONTAINER}>
        <span>
          <span style={BPM_DOT('#5DCAA5')} />
          Audio: {audioBPM ?? '—'}
        </span>
        <span>
          <span style={BPM_DOT('#85B7EB')} />
          Visual: {visualBPM ?? '—'}
        </span>
        <span>
          <span style={BPM_DOT('#E0E0E0')} />
          Script: {scriptBPM ?? '—'}
        </span>
      </div>
    </div>
  );
}
