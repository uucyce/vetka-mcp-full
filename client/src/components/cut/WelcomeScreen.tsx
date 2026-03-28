/**
 * MARKER_GAMMA-APP1: Welcome / New Project screen.
 *
 * Shown when no project is loaded (projectId is empty).
 * Features:
 *   - Create New Project (name + location + preset)
 *   - Recent Projects list (localStorage)
 *   - Open Project file picker
 *   - CUT branding (monochrome)
 */
import { useState, useCallback, type CSSProperties } from 'react';

const LS_RECENT_PROJECTS = 'cut_recent_projects';

export interface RecentProject {
  id: string;
  name: string;
  path: string;
  lastOpened: number;
}

export function loadRecent(): RecentProject[] {
  try {
    const raw = localStorage.getItem(LS_RECENT_PROJECTS);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function saveRecent(projects: RecentProject[]) {
  try { localStorage.setItem(LS_RECENT_PROJECTS, JSON.stringify(projects.slice(0, 10))); } catch { /* ok */ }
}

export function addRecentProject(id: string, name: string, path: string) {
  const recent = loadRecent().filter((p) => p.id !== id);
  recent.unshift({ id, name, path, lastOpened: Date.now() });
  saveRecent(recent);
}

// ─── Styles ───

const ROOT: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  width: '100%',
  height: '100%',
  background: '#0a0a0a',
  fontFamily: 'system-ui, -apple-system, sans-serif',
  color: '#ccc',
};

const CARD: CSSProperties = {
  background: '#111',
  border: '1px solid #222',
  borderRadius: 8,
  padding: '32px 40px',
  width: 400,
  maxWidth: '90vw',
};

const TITLE: CSSProperties = {
  fontSize: 24,
  fontWeight: 300,
  color: '#ccc',
  letterSpacing: '2px',
  textAlign: 'center',
  marginBottom: 4,
};

const SUBTITLE: CSSProperties = {
  fontSize: 10,
  color: '#555',
  textAlign: 'center',
  letterSpacing: '1px',
  textTransform: 'uppercase',
  marginBottom: 24,
};

const INPUT: CSSProperties = {
  width: '100%',
  padding: '8px 12px',
  background: '#0a0a0a',
  border: '1px solid #333',
  borderRadius: 4,
  color: '#ccc',
  fontSize: 12,
  outline: 'none',
  boxSizing: 'border-box',
  marginBottom: 12,
};

const BTN_PRIMARY: CSSProperties = {
  width: '100%',
  padding: '10px',
  background: '#222',
  border: '1px solid #444',
  borderRadius: 4,
  color: '#ccc',
  fontSize: 12,
  cursor: 'pointer',
  letterSpacing: '0.5px',
  marginBottom: 8,
};

const BTN_SECONDARY: CSSProperties = {
  ...BTN_PRIMARY,
  background: '#111',
  border: '1px solid #333',
  color: '#888',
};

const SECTION_TITLE: CSSProperties = {
  fontSize: 9,
  color: '#555',
  textTransform: 'uppercase',
  letterSpacing: '1px',
  marginBottom: 8,
  marginTop: 20,
};

const RECENT_ITEM: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '6px 8px',
  borderRadius: 4,
  cursor: 'pointer',
  fontSize: 11,
  marginBottom: 2,
};

// ─── FPS + Resolution presets (FCP7 / Premiere industry standard) ───

const STANDARD_FRAMERATES = [
  { fps: 23.976, label: '23.976', desc: 'Film (NTSC pulldown)' },
  { fps: 24,     label: '24',     desc: 'Cinema standard' },
  { fps: 25,     label: '25',     desc: 'PAL / European broadcast' },
  { fps: 29.97,  label: '29.97',  desc: 'NTSC broadcast' },
  { fps: 30,     label: '30',     desc: 'Web / progressive' },
  { fps: 48,     label: '48',     desc: 'HFR cinema (The Hobbit)' },
  { fps: 50,     label: '50',     desc: 'PAL high frame rate' },
  { fps: 59.94,  label: '59.94',  desc: 'NTSC high frame rate' },
  { fps: 60,     label: '60',     desc: 'Web / gaming / sports' },
];

const RESOLUTION_PRESETS = [
  { id: '4k',      w: 3840, h: 2160, label: '4K UHD',     ratio: '16:9' },
  { id: '4k_dci',  w: 4096, h: 2160, label: '4K DCI',     ratio: '1.9:1' },
  { id: '1080p',   w: 1920, h: 1080, label: '1080p HD',   ratio: '16:9' },
  { id: '720p',    w: 1280, h: 720,  label: '720p HD',    ratio: '16:9' },
  { id: '1080v',   w: 1080, h: 1920, label: '1080 Vert.', ratio: '9:16' },
  { id: '1080sq',  w: 1080, h: 1080, label: '1080 Sq.',   ratio: '1:1' },
];

const SELECT_STYLE: CSSProperties = {
  width: '100%',
  padding: '6px 8px',
  background: '#0a0a0a',
  border: '1px solid #333',
  borderRadius: 4,
  color: '#ccc',
  fontSize: 11,
  outline: 'none',
  marginBottom: 8,
};

// ─── Component ───

interface WelcomeScreenProps {
  onCreateProject: (name: string, preset: string) => void;
  onOpenProject: (id: string, path: string) => void;
}

export default function WelcomeScreen({ onCreateProject, onOpenProject }: WelcomeScreenProps) {
  const [projectName, setProjectName] = useState('');
  const [fps, setFps] = useState(24);
  const [resolution, setResolution] = useState('1080p');
  const [customFps, setCustomFps] = useState('');
  const [recentProjects] = useState(loadRecent);

  const handleCreate = useCallback(() => {
    const name = projectName.trim() || 'Untitled';
    const res = RESOLUTION_PRESETS.find((r) => r.id === resolution) || RESOLUTION_PRESETS[2];
    const preset = `${res.w}x${res.h}@${fps}`;
    onCreateProject(name, preset);
  }, [projectName, fps, resolution, onCreateProject]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleCreate();
  }, [handleCreate]);

  return (
    <div style={ROOT}>
      <div style={CARD}>
        <div style={TITLE}>CUT</div>
        <div style={SUBTITLE}>Cognitive Universal Timeline</div>

        {/* New Project */}
        <div style={SECTION_TITLE}>New Project</div>
        <input
          type="text"
          placeholder="Project name..."
          value={projectName}
          onChange={(e) => setProjectName(e.target.value)}
          onKeyDown={handleKeyDown}
          style={INPUT}
          autoFocus
        />
        {/* Resolution */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 8, color: '#555', marginBottom: 3, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Resolution</div>
            <select
              value={resolution}
              onChange={(e) => setResolution(e.target.value)}
              style={SELECT_STYLE}
            >
              {RESOLUTION_PRESETS.map((r) => (
                <option key={r.id} value={r.id}>{r.label} ({r.w}x{r.h})</option>
              ))}
            </select>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 8, color: '#555', marginBottom: 3, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Frame Rate</div>
            <select
              value={fps}
              onChange={(e) => {
                const v = parseFloat(e.target.value);
                if (v === -1) return; // custom — handled below
                setFps(v);
                setCustomFps('');
              }}
              style={SELECT_STYLE}
            >
              {STANDARD_FRAMERATES.map((f) => (
                <option key={f.fps} value={f.fps}>{f.label} fps — {f.desc}</option>
              ))}
              <option value={-1}>Custom...</option>
            </select>
          </div>
        </div>
        {/* Custom FPS input */}
        {fps === -1 || (customFps !== '' && !STANDARD_FRAMERATES.some((f) => f.fps === fps)) ? (
          <div style={{ marginBottom: 8 }}>
            <input
              type="number"
              min={1}
              max={120}
              step={0.001}
              placeholder="Custom fps (1-120)..."
              value={customFps}
              onChange={(e) => {
                setCustomFps(e.target.value);
                const v = parseFloat(e.target.value);
                if (!isNaN(v) && v >= 1 && v <= 120) setFps(v);
              }}
              style={{ ...INPUT, marginBottom: 0 }}
            />
            <div style={{ fontSize: 8, color: '#444', marginTop: 2 }}>Backend accepts 1-120 fps</div>
          </div>
        ) : null}
        <button style={BTN_PRIMARY} onClick={handleCreate}>
          Create Project
        </button>

        {/* Open Project */}
        <button style={BTN_SECONDARY} onClick={() => onOpenProject('', '')}>
          Open Project...
        </button>

        {/* Recent Projects */}
        {recentProjects.length > 0 && (
          <>
            <div style={SECTION_TITLE}>Recent Projects</div>
            {recentProjects.map((proj) => (
              <div
                key={proj.id}
                style={RECENT_ITEM}
                onClick={() => onOpenProject(proj.id, proj.path)}
                onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = '#1a1a1a'; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
              >
                <div>
                  <div style={{ color: '#ccc' }}>{proj.name}</div>
                  <div style={{ fontSize: 9, color: '#555', marginTop: 1 }}>{proj.path}</div>
                </div>
                <span style={{ fontSize: 8, color: '#444' }}>
                  {new Date(proj.lastOpened).toLocaleDateString()}
                </span>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
