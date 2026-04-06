/**
 * MARKER_QA.W5.1: DebugShellPanel — Legacy debug shell for E2E smoke tests.
 *
 * Renders project state, runtime flags, selected shot info, and worker controls
 * when viewMode === 'debug'. Reads from useCutEditorStore.debugProjectState
 * which is synced from CutStandalone.
 */
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { useSelectionStore } from '../../store/useSelectionStore';
import type { CSSProperties } from 'react';

// ─── Styles ───
const SHELL: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  background: '#0a0a0a',
  color: '#ccc',
  fontFamily: 'monospace',
  fontSize: 11,
  overflow: 'auto',
  padding: 12,
  gap: 8,
};
const TITLE: CSSProperties = { fontSize: 16, fontWeight: 700, color: '#fff', marginBottom: 4 };
const SECTION: CSSProperties = { background: '#111', border: '1px solid #222', borderRadius: 4, padding: 8 };
const SECTION_TITLE: CSSProperties = { fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 4 };
const BTN: CSSProperties = {
  padding: '4px 10px', fontSize: 10, fontFamily: 'monospace',
  background: '#1a1a1a', color: '#ccc', border: '1px solid #333',
  borderRadius: 3, cursor: 'pointer',
};
const MUTED: CSSProperties = { color: '#666' };
const ROW: CSSProperties = { display: 'flex', flexWrap: 'wrap' as const, gap: 6 };

type PS = Record<string, unknown>;

function flag(ps: PS | null, key: string): string {
  if (!ps) return `${key}: unknown`;
  return `${key}: ${String(ps[key] ?? 'unknown')}`;
}

export default function DebugShellPanel() {
  const ps = useCutEditorStore((s) => s.debugProjectState) as PS | null;
  const status = useCutEditorStore((s) => s.debugStatus);
  const handlers = useCutEditorStore((s) => s.debugHandlers);
  const lanes = useCutEditorStore((s) => s.lanes);
  const thumbnails = useCutEditorStore((s) => s.thumbnails);
  const selectedClipId = useSelectionStore((s) => s.selectedClipId);

  const project = (ps?.project || {}) as PS;
  const displayName = String(project.display_name || project.project_id || 'Unknown');
  const projectId = String(project.project_id || '');

  // Selected shot info — prefer clip selection, fall back to first thumbnail
  let selectedSourcePath = '';
  let selectedFileName = '';

  // Try clip selection first
  for (const lane of lanes) {
    const clip = lane.clips.find((c: { clip_id: string }) => c.clip_id === selectedClipId);
    if (clip) {
      selectedSourcePath = String((clip as unknown as PS).source_path || '');
      break;
    }
  }
  // Fallback to first thumbnail (old debug shell behavior)
  if (!selectedSourcePath && thumbnails.length > 0) {
    selectedSourcePath = String(thumbnails[0].source_path || '');
  }
  selectedFileName = selectedSourcePath.split('/').pop() || '';

  // CAM markers for selected shot — read from raw project state (has cam_payload field)
  const rawMarkerItems = ((ps?.time_marker_bundle as PS)?.items || []) as PS[];
  const selectedShotMarkers = rawMarkerItems.filter(
    (m) => String(m.media_path || '') === selectedSourcePath
  );
  const camMarkers = selectedShotMarkers.filter((m) => m.cam_payload);
  const hasCamPayloads = camMarkers.length > 0;

  // Timeline info
  const timelineState = (ps?.timeline_state || {}) as PS;
  const tlLanes = (timelineState.lanes || []) as PS[];

  // Worker output counts
  const waveformCount = ((ps?.waveform_bundle as PS)?.items as unknown[] || []).length;
  const audioSyncCount = ((ps?.audio_sync_result as PS)?.items as unknown[] || []).length;
  const syncSurfaceCount = ((ps?.sync_surface as PS)?.items as unknown[] || []).length;
  const timeMarkerCount = ((ps?.time_marker_bundle as PS)?.items as unknown[] || []).length;
  const thumbnailCount = ((ps?.thumbnail_bundle as PS)?.items as unknown[] || []).length;
  const sliceCount = ((ps?.slice_bundle as PS)?.items as unknown[] || []).length;

  // Jobs
  const recentJobs = (ps?.recent_jobs || []) as PS[];
  const activeJobs = (ps?.active_jobs || []) as PS[];

  return (
    <div style={SHELL}>
      <div style={TITLE}>VETKA CUT</div>
      <div>{status}</div>
      <div>{projectId}</div>

      {/* Action Buttons */}
      <div style={ROW}>
        <button style={BTN} onClick={() => handlers?.bootstrap?.()}>Open CUT Project</button>
        <button style={BTN} onClick={() => handlers?.sceneAssembly?.()}>Start Scene Assembly</button>
        <button style={BTN} onClick={() => handlers?.selectFirstClip?.()}>Select First Clip</button>
        <button style={BTN} onClick={() => handlers?.refreshProjectState?.()}>Refresh Project State</button>
      </div>

      {/* Project Overview */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>Project Overview</div>
        <div>{displayName}</div>
        <div style={MUTED}>sandbox: {String(ps?.project && (project.sandbox_root || ''))}</div>
      </div>

      {/* Runtime Flags */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>Runtime Flags</div>
        <div>{flag(ps, 'runtime_ready')}</div>
        <div>{flag(ps, 'graph_ready')}</div>
        <div>{flag(ps, 'waveform_ready')}</div>
        <div>{flag(ps, 'transcript_ready')}</div>
        <div>{flag(ps, 'thumbnail_ready')}</div>
        <div>{flag(ps, 'audio_sync_ready')}</div>
        <div>{flag(ps, 'slice_ready')}</div>
        <div>{flag(ps, 'timecode_sync_ready')}</div>
        <div>{flag(ps, 'sync_surface_ready')}</div>
        <div>{flag(ps, 'meta_sync_ready')}</div>
        <div>{flag(ps, 'time_markers_ready')}</div>
      </div>

      {/* Timeline Surface */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>Timeline Surface</div>
        {tlLanes.length === 0 && <div style={MUTED}>Run scene assembly.</div>}
        {tlLanes.map((lane, i) => {
          const laneId = String(lane.lane_id || `lane_${i}`);
          const laneType = String(lane.lane_type || 'unknown');
          const clips = (lane.clips || []) as PS[];
          return (
            <div key={laneId}>
              <div>{laneType} / {laneType}</div>
              {clips.map((clip, j) => {
                const clipId = String(clip.clip_id || `clip_${j}`);
                const sceneId = String(clip.scene_id || '');
                return <div key={clipId} style={MUTED}>{sceneId || clipId}</div>;
              })}
            </div>
          );
        })}
      </div>

      {/* Selected Shot */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>Selected Shot</div>
        {selectedSourcePath ? (
          <div>{selectedFileName}</div>
        ) : (
          <div style={MUTED}>No clip selected</div>
        )}
      </div>

      {/* CAM Ready */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>CAM Ready</div>
        <div>cam markers: {selectedShotMarkers.filter(m => m.kind === 'cam').length}</div>
        {!hasCamPayloads && (
          <>
            <div>status: waiting for CAM payloads</div>
            <div>next: attach `cam_payload` and contextual hints for this shot</div>
          </>
        )}
        {hasCamPayloads && (
          <>
            <div>status: context-linked markers detected</div>
            {camMarkers.map((m, i) => {
              const cp = (m as Record<string, unknown>).cam_payload as PS | null;
              return (
                <div key={i}>
                  <div>{Number(m.start_sec)}s - {Number(m.end_sec)}s</div>
                  {cp && <div>source: {String(cp.source)} · status: {String(cp.status)}</div>}
                  {cp && String(cp.hint || '') !== '' && <div>{String(cp.hint)}</div>}
                </div>
              );
            })}
          </>
        )}
      </div>

      {/* Worker Outputs */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>Worker Outputs</div>
        <div>waveforms: {waveformCount}</div>
        <div>audio_sync: {audioSyncCount}</div>
        <div>thumbnails: {thumbnailCount}</div>
        <div>slices: {sliceCount}</div>
        <div>sync_surface: {syncSurfaceCount}</div>
        <div>time_markers: {timeMarkerCount}</div>
        {/* Sync surface items */}
        {((ps?.sync_surface as PS)?.items as PS[] || []).map((item, i) => (
          <div key={i}>SYNC · {String(item.source_path || '').split('/').pop()}</div>
        ))}
      </div>

      {/* Worker Controls */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>Worker Actions</div>
        <div style={ROW}>
          <button style={BTN} onClick={() => handlers?.waveformBuild?.()}>Build Waveforms</button>
          <button style={BTN} onClick={() => handlers?.audioSyncBuild?.()}>Build Audio Sync</button>
          <button style={BTN} onClick={() => handlers?.thumbnailBuild?.()}>Build Thumbnails</button>
          <button style={BTN} onClick={() => handlers?.pauseSliceBuild?.()}>Build Pause Slices</button>
          <button style={BTN} onClick={() => handlers?.timecodeSyncBuild?.()}>Build Timecode Sync</button>
          <button style={BTN} onClick={() => handlers?.metaSync?.()}>Build Meta Sync</button>
        </div>
      </div>

      {/* Worker Queue */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>Worker Queue</div>
        <div>active: {activeJobs.length}</div>
        <div>recent: {recentJobs.length}</div>
        {activeJobs.map((job, i) => (
          <div key={i}>
            <span>{String(job.job_id || '').slice(0, 8)}...</span>
            <span style={MUTED}> {String(job.state || 'unknown')}</span>
            {handlers && (
              <button style={{ ...BTN, marginLeft: 4 }} onClick={() => {
                // Cancel via API
                const jobId = String(job.job_id || '');
                if (jobId) {
                  fetch(`/api/cut/job/${encodeURIComponent(jobId)}/cancel`, { method: 'POST' });
                  handlers.refreshProjectState?.();
                }
              }}>Cancel</button>
            )}
          </div>
        ))}
      </div>

      {/* Thumbnails / Source Browser items */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>Source Browser</div>
        {thumbnails.map((t, i) => (
          <div key={i}>{String(t.source_path || '').split('/').pop()}</div>
        ))}
      </div>

      {/* Inspector / Questions */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>Inspector / Questions</div>
        <div style={MUTED}>Bootstrap stats</div>
        <pre style={{ fontSize: 9, whiteSpace: 'pre-wrap', color: '#888' }}>
          {JSON.stringify(ps?.bootstrap_state || {}, null, 2)}
        </pre>
      </div>

      {/* Storyboard Strip */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>Storyboard Strip</div>
        {thumbnails.length === 0 && <div style={MUTED}>No thumbnails</div>}
        {thumbnails.length > 0 && <div>{thumbnails.length} card(s)</div>}
      </div>

      {/* Sync Hints */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>Sync Hints</div>
        <div>sync items: {syncSurfaceCount}</div>
        {((ps?.sync_surface as PS)?.items as PS[] || []).map((item, i) => (
          <div key={i}>
            <div>{String(item.source_path || '').split('/').pop()}: {String(item.recommended_method || 'none')} ({String(item.confidence || 0)})</div>
          </div>
        ))}
      </div>

      {/* Time Markers */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>Time Markers</div>
        <div>markers: {timeMarkerCount}</div>
        {((ps?.time_marker_bundle as PS)?.items as PS[] || []).map((m, i) => {
          const kind = String((m as PS).kind || 'unknown');
          const markerStatus = String((m as PS).status || 'active');
          return (
            <div key={i}>
              {kind}: {String((m as PS).text || '')} ({markerStatus})
              {' '}{String((m as PS).media_path || '').split('/').pop()}
            </div>
          );
        })}
      </div>
    </div>
  );
}
