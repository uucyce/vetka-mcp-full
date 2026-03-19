/**
 * MARKER_W5.1: Auto-Montage Menu — dropdown with 3 PULSE modes.
 *
 * Modes:
 * - Favorites Cut (★) — assembles from favorite markers
 * - Script Cut (¶) — matches script scenes to materials
 * - Music Cut (♩) — matches materials to music via Camelot/mood
 *
 * Each mode calls POST /cut/pulse/auto-montage → creates new timeline tab.
 * Progress indicator during assembly. Backend is 100% ready.
 */
import { useState, useRef, useEffect, useCallback, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { API_BASE } from '../../config/api.config';

// ─── Types ───

type MontageMode = 'favorites' | 'script' | 'music';

interface ModeOption {
  mode: MontageMode;
  icon: string;
  label: string;
  description: string;
}

const MODES: ModeOption[] = [
  { mode: 'favorites', icon: '★', label: 'Favorites Cut', description: 'Assemble from favorite markers' },
  { mode: 'script', icon: '¶', label: 'Script Cut', description: 'Match script scenes to materials' },
  { mode: 'music', icon: '♩', label: 'Music Cut', description: 'Sync materials to music BPM' },
];

// ─── Styles ───

const TRIGGER_BTN: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 4,
  height: 24,
  padding: '0 8px',
  fontSize: 10,
  color: '#888',
  cursor: 'pointer',
  background: 'none',
  border: '1px solid #333',
  borderRadius: 3,
  marginLeft: 8,
  fontFamily: 'system-ui',
  whiteSpace: 'nowrap',
};

const DROPDOWN: CSSProperties = {
  position: 'absolute',
  top: '100%',
  left: 0,
  marginTop: 4,
  background: '#1a1a1a',
  border: '1px solid #333',
  borderRadius: 4,
  padding: 4,
  minWidth: 200,
  zIndex: 100,
  boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
};

const MODE_BTN: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  width: '100%',
  padding: '6px 8px',
  fontSize: 11,
  color: '#ccc',
  cursor: 'pointer',
  background: 'none',
  border: 'none',
  borderRadius: 3,
  textAlign: 'left',
  fontFamily: 'system-ui',
};

const PROGRESS_BAR_OUTER: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  marginLeft: 8,
  height: 24,
  fontSize: 10,
  color: '#888',
  fontFamily: 'system-ui',
};

const PROGRESS_BAR_INNER: CSSProperties = {
  width: 80,
  height: 4,
  background: '#222',
  borderRadius: 2,
  overflow: 'hidden',
};

// ─── Component ───

export default function AutoMontageMenu() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const montageRunning = useCutEditorStore((s) => s.montageRunning);
  const montageProgress = useCutEditorStore((s) => s.montageProgress);
  const montageError = useCutEditorStore((s) => s.montageError);
  const setMontageRunning = useCutEditorStore((s) => s.setMontageRunning);
  const setMontageMode = useCutEditorStore((s) => s.setMontageMode);
  const setMontageProgress = useCutEditorStore((s) => s.setMontageProgress);
  const setMontageError = useCutEditorStore((s) => s.setMontageError);
  const createVersionedTimeline = useCutEditorStore((s) => s.createVersionedTimeline);
  const projectId = useCutEditorStore((s) => s.projectId);
  const timelineId = useCutEditorStore((s) => s.timelineId);
  const nextTimelineVersion = useCutEditorStore((s) => s.nextTimelineVersion);

  // Close dropdown on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const runMontage = useCallback(async (mode: MontageMode) => {
    setOpen(false);
    setMontageRunning(true);
    setMontageMode(mode);
    setMontageError(null);
    setMontageProgress('Preparing...');

    const projectName = projectId || 'project';

    try {
      setMontageProgress('Analyzing materials...');

      const body: Record<string, unknown> = {
        mode,
        project_name: projectName,
        version: nextTimelineVersion,
        timeline_id: timelineId,
      };

      // Mode-specific defaults
      if (mode === 'favorites') {
        body.order_by = 'time';
      } else if (mode === 'script') {
        body.script_text = ''; // backend loads from project store
      } else if (mode === 'music') {
        body.music_bpm = 120.0;
        body.music_key = '8B';
        body.music_camelot_key = '8B';
      }

      setMontageProgress('Building timeline...');

      const res = await fetch(`${API_BASE}/cut/pulse/auto-montage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      const data = await res.json();

      if (!data.success) {
        throw new Error(data.error || 'Auto-montage failed');
      }

      setMontageProgress('Creating tab...');

      // Create new versioned timeline tab with the result
      createVersionedTimeline(projectName, mode);

      setMontageProgress(`Done: ${data.clip_count ?? 0} clips, ${(data.total_duration ?? 0).toFixed(1)}s`);

      // Clear progress after 3s
      setTimeout(() => {
        setMontageRunning(false);
        setMontageMode(null);
        setMontageProgress(null);
      }, 3000);

    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setMontageError(msg);
      setMontageProgress(null);
      // Clear error after 5s
      setTimeout(() => {
        setMontageRunning(false);
        setMontageMode(null);
        setMontageError(null);
      }, 5000);
    }
  }, [projectId, timelineId, nextTimelineVersion, createVersionedTimeline,
      setMontageRunning, setMontageMode, setMontageProgress, setMontageError]);

  // ─── Running state: show progress ───
  if (montageRunning && !montageError) {
    return (
      <div style={PROGRESS_BAR_OUTER}>
        <div style={PROGRESS_BAR_INNER}>
          <div style={{
            width: '100%',
            height: '100%',
            background: '#4a9eff',
            borderRadius: 2,
            animation: 'pulse-montage 1.2s ease-in-out infinite',
          }} />
        </div>
        <span>{montageProgress || 'Working...'}</span>
        <style>{`
          @keyframes pulse-montage {
            0%, 100% { opacity: 0.4; }
            50% { opacity: 1; }
          }
        `}</style>
      </div>
    );
  }

  // ─── Error state ───
  if (montageError) {
    return (
      <div style={{ ...PROGRESS_BAR_OUTER, color: '#e55' }}>
        <span>Montage error: {montageError}</span>
      </div>
    );
  }

  // ─── Dropdown trigger ───
  return (
    <div ref={ref} style={{ position: 'relative', display: 'inline-flex' }}>
      <button
        style={TRIGGER_BTN}
        onClick={() => setOpen(!open)}
        title="PULSE Auto-Montage: create timeline from favorites, script, or music"
      >
        <span style={{ fontSize: 12 }}>PULSE</span>
        <span style={{ fontSize: 8, color: '#555' }}>&#9660;</span>
      </button>

      {open && (
        <div style={DROPDOWN}>
          {MODES.map((opt) => (
            <button
              key={opt.mode}
              style={MODE_BTN}
              onClick={() => runMontage(opt.mode)}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.background = '#252525';
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.background = 'none';
              }}
            >
              <span style={{ fontSize: 14, width: 18, textAlign: 'center', color: '#666' }}>
                {opt.icon}
              </span>
              <div>
                <div style={{ fontWeight: 500 }}>{opt.label}</div>
                <div style={{ fontSize: 9, color: '#666', marginTop: 1 }}>{opt.description}</div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
