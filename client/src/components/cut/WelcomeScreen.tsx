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

interface RecentProject {
  id: string;
  name: string;
  path: string;
  lastOpened: number;
}

function loadRecent(): RecentProject[] {
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

// ─── Presets ───

const PROJECT_PRESETS = [
  { id: 'film', label: 'Film (24fps, ProRes)' },
  { id: 'web', label: 'Web (30fps, H.264)' },
  { id: 'social', label: 'Social (30fps, 1080p vertical)' },
];

// ─── Component ───

interface WelcomeScreenProps {
  onCreateProject: (name: string, preset: string) => void;
  onOpenProject: (id: string, path: string) => void;
}

export default function WelcomeScreen({ onCreateProject, onOpenProject }: WelcomeScreenProps) {
  const [projectName, setProjectName] = useState('');
  const [preset, setPreset] = useState('film');
  const [recentProjects] = useState(loadRecent);

  const handleCreate = useCallback(() => {
    const name = projectName.trim() || 'Untitled';
    onCreateProject(name, preset);
  }, [projectName, preset, onCreateProject]);

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
        <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
          {PROJECT_PRESETS.map((p) => (
            <button
              key={p.id}
              onClick={() => setPreset(p.id)}
              style={{
                flex: 1,
                padding: '4px',
                background: preset === p.id ? '#222' : '#111',
                border: `1px solid ${preset === p.id ? '#555' : '#333'}`,
                borderRadius: 3,
                color: preset === p.id ? '#ccc' : '#666',
                fontSize: 9,
                cursor: 'pointer',
              }}
            >
              {p.label}
            </button>
          ))}
        </div>
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
