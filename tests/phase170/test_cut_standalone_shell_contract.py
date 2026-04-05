import pytest
from pathlib import Path

pytestmark = pytest.mark.stale(reason="CUT API refactored — bootstrap/project_state contracts changed")

ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_cut_standalone_shell_route_registered():
    main_tsx = _read("client/src/main.tsx")

    assert "import CutStandalone from './CutStandalone';" in main_tsx
    assert "pathname === '/cut'" in main_tsx
    assert "return <CutStandalone />;" in main_tsx


def test_cut_standalone_shell_binds_to_cut_mcp_contracts():
    shell = _read("client/src/CutStandalone.tsx")

    assert "import { NOLAN_PALETTE } from './utils/dagLayout';" in shell
    assert "buildCutSceneGraphViewportModel" in shell
    assert "DAGView" in shell
    assert "Open CUT Project" in shell
    assert "Start Scene Assembly" in shell
    assert "Build Waveforms" in shell
    assert "Normalize Transcripts" in shell
    assert "Build Thumbnails" in shell
    assert "Build Timecode Sync" in shell
    assert "Build Audio Sync" in shell
    assert "Build Pause Slices" in shell
    assert "Player Lab Import" in shell
    assert "Pick Player Lab JSON" in shell
    assert "Import Player Lab Markers" in shell
    assert "No Player Lab file loaded." in shell
    assert "/cut/markers/import-player-lab" in shell
    assert "Favorite Moment" in shell
    assert "Comment Marker" in shell
    assert "CAM Marker" in shell
    assert "Archive Marker" in shell
    assert "Cognitive Markers" in shell
    assert "time_markers_ready:" in shell
    assert "preview_window_v1" in shell
    assert "transcript_pause_window_v1" in shell
    assert "energy_pause_v1" in shell
    assert "marker window" in shell
    assert "slice:" in shell
    assert "slice source:" in shell
    assert "sync hint:" in shell
    assert "timecode hint:" in shell
    assert "recommended sync:" in shell
    assert "window.setInterval" in shell
    assert "activeJobs.length === 0" in shell
    assert "Selected Shot" in shell
    assert "Select Shot" in shell
    assert "Sync Timeline Selection" in shell
    assert "Apply Sync Offset" in shell
    assert "timeline link:" in shell
    assert "timeline selected" in shell
    assert "markers for shot:" in shell
    assert "Favorite Markers" in shell
    assert "Comment Markers" in shell
    assert "CAM Markers" in shell
    assert "Other Markers" in shell
    assert "CAM Ready" in shell
    assert "waiting for CAM payloads" in shell
    assert "source:" in shell
    assert "no cam hint yet" in shell
    assert "Show Active Only" in shell
    assert "Show All Markers" in shell
    assert "Show All Global Markers" in shell
    assert "Show Active Global Only" in shell
    assert "No visible cognitive markers." in shell
    assert "No markers for selected shot." in shell
    assert "Focus Marker In Timeline" in shell
    assert "selectedMarkerId" in shell
    assert "Favorite Selected" in shell
    assert "Comment Selected" in shell
    assert "CAM Selected" in shell
    assert "Open Preview" in shell
    assert "Worker Queue" in shell
    assert "Sync Hints" in shell
    assert "timecode_sync results:" in shell
    assert "sync_surface items:" in shell
    assert "Storyboard Strip" in shell
    assert "viewport roots:" in shell
    assert "Scene Graph DAG viewport is explicit." in shell
    assert "Graph focus follows storyboard + timeline context through source-path and clip crosslinks." in shell
    assert "Embed In Flow" in shell
    assert "Promote To Peer Pane" in shell
    assert "peer product surface preview" in shell
    assert "embedded debug-shell flow" in shell
    assert "right peer pane beside timeline/storyboard stack" in shell
    assert "inline shell flow card" in shell
    assert "CUT_SCENE_GRAPH_PANE_MODE_STORAGE_KEY" in shell
    assert "readStoredSceneGraphPaneMode" in shell
    assert "persistSceneGraphPaneMode" in shell
    assert "cut.scene_graph.pane_mode.v1" in shell
    assert "pane mode restores on CUT reload via localStorage preference" in shell
    assert "Scene Graph Inspector" in shell
    assert "first-class viewport adapter ready:" in shell
    assert "handleSceneGraphNodeSelect" in shell
    assert "Graph focus -> timeline:" in shell
    assert "cut_scene_graph_viewport" in shell
    assert "graph-linked nodes:" in shell
    assert "graph primary:" in shell
    assert "graph render mode:" in shell
    assert "graph summary:" in shell
    assert "graph focus source:" in shell
    assert "graph marker budget:" in shell
    assert "graph sync badges:" in shell
    assert "graph buckets:" in shell
    assert "graph inspector link:" in shell
    assert "graph sync " in shell
    assert "graph bucket " in shell
    assert "no graph sync chips" in shell
    assert "selected-shot linked inspector node" in shell
    assert "active_jobs:" in shell
    assert "recent_jobs:" in shell
    assert "Cancel Job" in shell
    assert "/cut/bootstrap" in shell
    assert "/cut/project-state" in shell
    assert "/cut/job/" in shell
    assert "/cancel" in shell
    assert "/cut/scene-assembly-async" in shell
    assert "/cut/worker/waveform-build-async" in shell
    assert "/cut/worker/transcript-normalize-async" in shell
    assert "/cut/worker/thumbnail-build-async" in shell
    assert "/cut/worker/timecode-sync-async" in shell
    assert "/cut/worker/audio-sync-async" in shell
    assert "/cut/worker/pause-slice-async" in shell
    assert "/cut/time-markers/apply" in shell
    assert "/cut/timeline/apply" in shell
    assert "/cut/scene-graph/apply" in shell
    assert "apply_sync_offset" in shell
    assert "#2563eb" not in shell


def test_cut_scene_graph_viewport_adapter_contract_present():
    adapter = _read("client/src/components/cut/sceneGraphViewportAdapter.ts")

    assert "export type CutSceneGraphView" in adapter
    assert "export type CutSceneGraphViewportModel" in adapter
    assert "export function buildCutSceneGraphViewportModel" in adapter
    assert "render_hints" in adapter
    assert "dag_projection" in adapter
    assert "inspectorNodes" in adapter
    assert "dagIdsByClipId" in adapter
    assert "dagIdsBySourcePath" in adapter
    assert "cardByNodeId" in adapter


def test_cut_timeline_volume_and_snap_hooks_present():
    timeline = _read("client/src/components/cut/TimelineTrackView.tsx")
    store = _read("client/src/store/useCutEditorStore.ts")
    audio_engine = _read("client/src/hooks/useAudioEngine.ts")
    layout = _read("client/src/components/cut/CutEditorLayout.tsx")

    assert "laneVolumes" in store
    assert "setLaneVolume" in store
    assert "snapEnabled" in store
    assert "toggleSnap" in store
    assert "TRACK_SLIDER_WRAP" in timeline
    assert "rotate(-90deg)" in timeline
    assert "Double-click reset lane volume to 100%" in timeline
    assert "MARKER_173.16.NLE.TRACK_VOLUME" in timeline
    assert "MARKER_170.NLE.SNAP_GRID" in timeline
    assert "MARKER_173.18.NLE.BEAT_SNAP" in timeline
    assert "playheadSec: currentTimeRef.current" in timeline
    assert "markerTimes: markerTimesRef.current" in timeline
    assert "event.altKey" in timeline
    assert "for (const lane of args.lanes)" in timeline
    assert "export default function useAudioEngine()" in audio_engine
    assert "MediaElementAudioSourceNode" in audio_engine
    assert "gainNode" in audio_engine
    assert "laneVolumes" in audio_engine
    assert "mutedLanes" in audio_engine
    assert "soloLanes" in audio_engine
    assert "clipLocalTime" in audio_engine
    assert "useAudioEngine();" in layout


def test_cut_nle_scene_graph_promotion_hooks_present():
    shell = _read("client/src/CutStandalone.tsx")
    store = _read("client/src/store/useCutEditorStore.ts")
    layout = _read("client/src/components/cut/CutEditorLayout.tsx")
    transport = _read("client/src/components/cut/TransportBar.tsx")

    assert "sceneGraphSurfaceMode" in store
    assert "setSceneGraphSurfaceMode" in store
    assert "editorSetSceneGraphSurfaceMode" in shell
    assert "nle_ready" in shell
    assert "Graph Ready" in transport
    assert "cut-undo-button" in transport
    assert "cut-redo-button" in transport
    assert "cut-undo-toast" in transport
    assert "/cut/undo-stack" in transport
    assert "runUndoAction('undo')" in transport
    assert "runUndoAction('redo')" in transport
    assert "Cmd/Ctrl+Z" in transport
    assert "Cmd/Ctrl+Shift+Z" in transport
    assert "Scene Graph peer pane ready" in layout
    assert "cut-media-import-dropzone" in layout
    assert "cut-media-import-path" in layout
    assert "cut-media-import-trigger" in layout
    assert "cut-media-folder-picker" in layout
    assert "cut-media-import-status" in layout
    assert "/cut/bootstrap-async" in layout
    assert "Drag media folder here or use folder/path import" in layout
    assert "sceneGraphSurface={nleSceneGraphSurface}" in shell
    assert "Shared DAG viewport mounted inside NLE pane." in shell
    assert "NLE pane now reuses the shared DAG viewport bridge." in shell
    assert "clip-linked graph nodes:" in shell
    assert "active graph node:" in shell
    assert "pane inspector link:" in shell
    assert "focus source:" in shell
    assert "graph buckets:" in shell
    assert "Focus Timeline From Graph" in shell
    assert "Focus Selected Shot" in shell
    assert "All Edges" in shell
    assert "Structural Only" in shell
    assert "Overlay Only" in shell
    assert "edge filter:" in shell
    assert "edge legend:" in shell
    assert "Viewport Priority" in shell
    assert "Selection Summary" in shell
    assert "Media Card" in shell
    assert "Actions" in shell
    assert "Hide Details" in shell
    assert "Show Details" in shell
    assert "secondary summaries collapsed" in shell
    assert "Compact Graph Card" in shell
    assert "no primary graph card" in shell
    assert "no poster preview" in shell
    assert "Open a CUT project and run scene assembly." in shell
    assert "posterUrl" in shell
    assert "no sync badge" in shell
    assert "bucket " in shell
    assert "inspector " in shell
    assert "no inspector chips" in shell
    assert "Primary Graph Mini Card" in shell
    assert "no graph poster reuse" in shell
    assert "no graph mini card" in shell
    assert "no mini summary" in shell
    assert "#22c55e" in shell
    assert "display unknown" in shell
    assert "markers " in shell
    assert "sceneGraphSurface?: ReactNode" in layout
    assert "sceneGraphSurface || (" in layout
