/**
 * MARKER_CUT_1.3: ScriptPanel — the spine of VETKA CUT.
 *
 * Displays screenplay text as clickable scene chunk blocks.
 * Each chunk = visual block with scene heading, timecode from API.
 * Click block → sync playhead + DAG + source monitor.
 * Auto-scroll on playback (teleprompter mode).
 *
 * Data source: POST /api/cut/script/parse → SceneChunk[]
 * Fallback: line-by-line display if no chunks available.
 */
import { useCallback, useEffect, useRef, useState, type CSSProperties } from 'react';
import { usePanelSyncStore } from '../../store/usePanelSyncStore';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { API_BASE } from '../../config/api.config';

// ─── Types ───

interface SceneChunk {
  chunk_id: string;
  scene_heading: string | null;
  chunk_type: string;
  text: string;
  start_sec: number;
  duration_sec: number;
  line_start: number;
  line_end: number;
  page_count: number;
}

// ─── Styles ───

const PANEL: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  width: '100%',
  height: '100%',
  background: '#1A1A1A',
  overflow: 'hidden',
};

const CHUNK_LIST: CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  padding: '4px 0',
};

const CHUNK_BASE: CSSProperties = {
  padding: '8px 10px',
  borderLeft: '2px solid #333',
  marginBottom: 1,
  cursor: 'pointer',
  transition: 'all 0.12s',
};

const CHUNK_ACTIVE: CSSProperties = {
  ...CHUNK_BASE,
  borderLeftColor: '#4a9eff',
  background: 'rgba(74, 158, 255, 0.08)',
};

const CHUNK_HEADER: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  marginBottom: 4,
};

const CHUNK_TC: CSSProperties = {
  fontSize: 9,
  fontFamily: '"JetBrains Mono", monospace',
  color: '#555',
  minWidth: 36,
  flexShrink: 0,
};

const CHUNK_ID: CSSProperties = {
  fontSize: 8,
  fontFamily: '"JetBrains Mono", monospace',
  color: '#444',
};

const HEADING: CSSProperties = {
  fontWeight: 600,
  color: '#ccc',
  textTransform: 'uppercase',
  fontSize: 10,
  letterSpacing: '0.5px',
};

const CHUNK_TEXT: CSSProperties = {
  fontSize: 11,
  fontFamily: 'Inter, system-ui, sans-serif',
  color: '#777',
  lineHeight: 1.5,
  whiteSpace: 'pre-wrap',
  maxHeight: 80,
  overflow: 'hidden',
};

const EMPTY_STATE: CSSProperties = {
  padding: 16,
  color: '#555',
  fontSize: 11,
  textAlign: 'center',
};

// ─── Helpers ───

function formatTime(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

// ─── Component ───

interface ScriptPanelProps {
  scriptText?: string;
  activeTab?: string;
  onTabChange?: (tab: string) => void;
}

export default function ScriptPanel({ scriptText = '' }: ScriptPanelProps) {
  const [chunks, setChunks] = useState<SceneChunk[]>([]);
  const [activeChunkId, setActiveChunkId] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Sync store
  const syncFromScript = usePanelSyncStore((s) => s.syncFromScript);
  const playheadSec = usePanelSyncStore((s) => s.playheadSec);
  const lastSyncSource = usePanelSyncStore((s) => s.lastSyncSource);

  // Editor store
  const isPlaying = useCutEditorStore((s) => s.isPlaying);

  // ─── Parse script text into chunks via API ───
  useEffect(() => {
    if (!scriptText.trim()) {
      setChunks([]);
      return;
    }

    const controller = new AbortController();
    fetch(`${API_BASE}/cut/script/parse`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: scriptText }),
      signal: controller.signal,
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success && Array.isArray(data.chunks)) {
          setChunks(data.chunks);
        }
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          console.warn('[ScriptPanel] parse failed:', err);
        }
      });

    return () => controller.abort();
  }, [scriptText]);

  // ─── Click chunk → sync ───
  const handleChunkClick = useCallback(
    (chunk: SceneChunk) => {
      setActiveChunkId(chunk.chunk_id);
      syncFromScript(chunk.line_start, chunk.chunk_id, chunk.start_sec);
    },
    [syncFromScript],
  );

  // ─── Teleprompter auto-scroll during playback ───
  useEffect(() => {
    if (!isPlaying || !listRef.current || lastSyncSource === 'script' || chunks.length === 0) return;

    // Find the chunk that contains current playhead
    const targetIdx = chunks.findIndex(
      (c) => playheadSec >= c.start_sec && playheadSec < c.start_sec + c.duration_sec,
    );
    if (targetIdx < 0) return;

    const chunkEl = listRef.current.children[targetIdx] as HTMLElement | undefined;
    if (chunkEl) {
      chunkEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [playheadSec, isPlaying, chunks, lastSyncSource]);

  return (
    <div style={PANEL}>
      <div ref={listRef} style={CHUNK_LIST}>
        {chunks.length === 0 && (
          <div style={EMPTY_STATE}>
            No script loaded.
          </div>
        )}
        {chunks.map((chunk) => {
          const isActive = activeChunkId === chunk.chunk_id;
          return (
            <div
              key={chunk.chunk_id}
              style={isActive ? CHUNK_ACTIVE : CHUNK_BASE}
              onClick={() => handleChunkClick(chunk)}
            >
              {/* Header: timecode + chunk_id + scene heading */}
              <div style={CHUNK_HEADER}>
                <span style={CHUNK_TC}>{formatTime(chunk.start_sec)}</span>
                <span style={CHUNK_ID}>{chunk.chunk_id}</span>
              </div>
              {chunk.scene_heading && (
                <div style={HEADING}>{chunk.scene_heading}</div>
              )}
              {/* Body text (truncated) */}
              <div style={CHUNK_TEXT}>
                {chunk.text.split('\n').filter((l) => l.trim() && l !== chunk.scene_heading).slice(0, 4).join('\n')}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
