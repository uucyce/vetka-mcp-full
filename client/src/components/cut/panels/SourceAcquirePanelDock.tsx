/**
 * MARKER_SOURCE_ACQUIRE: Source Acquire panel — 4-tab ingest panel (FCP7 Log & Capture).
 * Tabs: YouTube fetch, AI Local, AI Remote, Local Import.
 * Monochrome: #1a1a1a bg, #222222 tabs, #888888 progress, zero color.
 */
import { type CSSProperties } from 'react';
import type { IDockviewPanelProps } from 'dockview-react';
import { useSourceAcquireStore, type AcquireTab } from '../../../store/sourceAcquireStore';

// ─── Tab definitions ────────────────────────────────────────────────

const TABS: { id: AcquireTab; label: string }[] = [
  { id: 'youtube', label: 'YouTube' },
  { id: 'ai-local', label: 'AI Local' },
  { id: 'ai-remote', label: 'AI Remote' },
  { id: 'import', label: 'Import' },
];

// ─── Styles (monochrome) ────────────────────────────────────────────

const PANEL_STYLE: CSSProperties = {
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  background: '#1a1a1a',
  color: '#ccc',
  fontFamily: 'system-ui',
  fontSize: 12,
  overflow: 'hidden',
};

const TAB_BAR_STYLE: CSSProperties = {
  display: 'flex',
  background: '#151515',
  borderBottom: '1px solid #333',
  flexShrink: 0,
};

const tabStyle = (active: boolean): CSSProperties => ({
  padding: '6px 14px',
  cursor: 'pointer',
  background: active ? '#222' : 'transparent',
  color: active ? '#ddd' : '#777',
  border: 'none',
  borderBottom: active ? '2px solid #888' : '2px solid transparent',
  fontSize: 11,
  fontWeight: active ? 600 : 400,
  letterSpacing: 0.3,
});

const CONTENT_STYLE: CSSProperties = {
  flex: 1,
  padding: 12,
  overflow: 'auto',
};

const QUEUE_STYLE: CSSProperties = {
  borderTop: '1px solid #333',
  padding: '8px 12px',
  background: '#151515',
  maxHeight: 120,
  overflow: 'auto',
  flexShrink: 0,
};

const JOB_ROW_STYLE: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  padding: '3px 0',
  fontSize: 11,
  color: '#999',
};

const PROGRESS_BG: CSSProperties = {
  flex: 1,
  height: 4,
  background: '#333',
  borderRadius: 2,
  overflow: 'hidden',
};

// ─── Tab content placeholders ───────────────────────────────────────

function YouTubeFetchTab() {
  const url = useSourceAcquireStore((s) => s.youtubeUrl);
  const setUrl = useSourceAcquireStore((s) => s.setYoutubeUrl);
  const quality = useSourceAcquireStore((s) => s.youtubeQuality);
  const setQuality = useSourceAcquireStore((s) => s.setYoutubeQuality);

  return (
    <div>
      <label style={{ display: 'block', marginBottom: 8, color: '#888', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>
        YouTube URL
      </label>
      <input
        type="text"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="https://youtube.com/watch?v=..."
        style={{
          width: '100%',
          padding: '6px 8px',
          background: '#222',
          border: '1px solid #444',
          borderRadius: 3,
          color: '#ccc',
          fontSize: 12,
          outline: 'none',
          boxSizing: 'border-box',
        }}
      />
      <div style={{ marginTop: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
        <span style={{ color: '#888', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Quality</span>
        <select
          value={quality}
          onChange={(e) => setQuality(e.target.value as typeof quality)}
          style={{ background: '#222', border: '1px solid #444', color: '#ccc', fontSize: 11, padding: '3px 6px', borderRadius: 3 }}
        >
          <option value="best">Best</option>
          <option value="1080p">1080p</option>
          <option value="720p">720p</option>
          <option value="480p">480p</option>
          <option value="audio-only">Audio Only</option>
        </select>
      </div>
      <div style={{ marginTop: 16, color: '#555', fontSize: 11 }}>
        Paste a YouTube URL and press I/O to mark segments for download.
      </div>
    </div>
  );
}

function AILocalTab() {
  const prompt = useSourceAcquireStore((s) => s.aiLocalPrompt);
  const setPrompt = useSourceAcquireStore((s) => s.setAiLocalPrompt);

  return (
    <div>
      <label style={{ display: 'block', marginBottom: 8, color: '#888', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>
        Prompt
      </label>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Describe what to generate..."
        rows={4}
        style={{
          width: '100%',
          padding: '6px 8px',
          background: '#222',
          border: '1px solid #444',
          borderRadius: 3,
          color: '#ccc',
          fontSize: 12,
          resize: 'vertical',
          outline: 'none',
          boxSizing: 'border-box',
          fontFamily: 'system-ui',
        }}
      />
      <div style={{ marginTop: 12, color: '#555', fontSize: 11 }}>
        Local AI generation (Stable Diffusion / Whisper TTS). Requires local backend.
      </div>
    </div>
  );
}

function AIRemoteTab() {
  const prompt = useSourceAcquireStore((s) => s.aiRemotePrompt);
  const setPrompt = useSourceAcquireStore((s) => s.setAiRemotePrompt);
  const provider = useSourceAcquireStore((s) => s.aiRemoteProvider);
  const setProvider = useSourceAcquireStore((s) => s.setAiRemoteProvider);

  return (
    <div>
      <div style={{ marginBottom: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
        <span style={{ color: '#888', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Provider</span>
        <select
          value={provider}
          onChange={(e) => setProvider(e.target.value as typeof provider)}
          style={{ background: '#222', border: '1px solid #444', color: '#ccc', fontSize: 11, padding: '3px 6px', borderRadius: 3 }}
        >
          <option value="runway">Runway</option>
          <option value="sora">Sora</option>
          <option value="kling">Kling</option>
        </select>
      </div>
      <label style={{ display: 'block', marginBottom: 8, color: '#888', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>
        Prompt
      </label>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Describe the video to generate..."
        rows={4}
        style={{
          width: '100%',
          padding: '6px 8px',
          background: '#222',
          border: '1px solid #444',
          borderRadius: 3,
          color: '#ccc',
          fontSize: 12,
          resize: 'vertical',
          outline: 'none',
          boxSizing: 'border-box',
          fontFamily: 'system-ui',
        }}
      />
      <div style={{ marginTop: 12, color: '#555', fontSize: 11 }}>
        Remote AI generation via cloud APIs. Credits tracking coming soon.
      </div>
    </div>
  );
}

function LocalImportTab() {
  const files = useSourceAcquireStore((s) => s.importFiles);
  const addFiles = useSourceAcquireStore((s) => s.addImportFiles);
  const clearFiles = useSourceAcquireStore((s) => s.clearImportFiles);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const paths = Array.from(e.dataTransfer.files).map((f) => f.name);
    if (paths.length > 0) addFiles(paths);
  };

  return (
    <div>
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        style={{
          border: '2px dashed #444',
          borderRadius: 6,
          padding: 24,
          textAlign: 'center',
          color: '#666',
          fontSize: 12,
          cursor: 'pointer',
          marginBottom: 12,
        }}
      >
        Drop media files here
      </div>
      {files.length > 0 && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ color: '#888', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>
              {files.length} file{files.length > 1 ? 's' : ''}
            </span>
            <button
              onClick={clearFiles}
              style={{ background: 'none', border: 'none', color: '#666', fontSize: 10, cursor: 'pointer' }}
            >
              Clear
            </button>
          </div>
          {files.map((f, i) => (
            <div key={i} style={{ padding: '2px 0', color: '#999', fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {f}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Acquire Queue widget ───────────────────────────────────────────

function AcquireQueue() {
  const jobs = useSourceAcquireStore((s) => s.jobs);
  if (jobs.length === 0) return null;

  return (
    <div style={QUEUE_STYLE}>
      <div style={{ color: '#888', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>
        Queue ({jobs.length})
      </div>
      {jobs.map((job) => (
        <div key={job.id} style={JOB_ROW_STYLE}>
          <span style={{ width: 60, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {job.type}
          </span>
          <span style={{ width: 80, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {job.label}
          </span>
          <div style={PROGRESS_BG}>
            <div style={{ width: `${job.progress * 100}%`, height: '100%', background: '#888', borderRadius: 2 }} />
          </div>
          <span style={{ width: 70, textAlign: 'right', fontSize: 10, color: '#666' }}>
            {job.status}
          </span>
        </div>
      ))}
    </div>
  );
}

// ─── Tab content router ─────────────────────────────────────────────

const TAB_CONTENT: Record<AcquireTab, React.FC> = {
  youtube: YouTubeFetchTab,
  'ai-local': AILocalTab,
  'ai-remote': AIRemoteTab,
  import: LocalImportTab,
};

// ─── Main panel ─────────────────────────────────────────────────────

export default function SourceAcquirePanelDock(_props: IDockviewPanelProps) {
  const activeTab = useSourceAcquireStore((s) => s.activeTab);
  const setActiveTab = useSourceAcquireStore((s) => s.setActiveTab);
  const TabContent = TAB_CONTENT[activeTab];

  return (
    <div style={PANEL_STYLE} data-testid="source-acquire-panel">
      <div style={TAB_BAR_STYLE}>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={tabStyle(activeTab === tab.id)}
            data-testid={`acquire-tab-${tab.id}`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div style={CONTENT_STYLE}>
        <TabContent />
      </div>
      <AcquireQueue />
    </div>
  );
}
