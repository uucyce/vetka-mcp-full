const POSTER_DATA_URL = `data:image/svg+xml;utf8,${encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180" viewBox="0 0 320 180">
  <rect width="320" height="180" fill="#111827"/>
  <rect x="12" y="12" width="296" height="156" rx="10" fill="#1f2937" stroke="#4b5563"/>
  <text x="28" y="70" fill="#f9fafb" font-family="Arial" font-size="20">VETKA CUT</text>
  <text x="28" y="102" fill="#9ca3af" font-family="Arial" font-size="14">Scene Graph Loaded Fixture</text>
</svg>
`)}`;

function createLoadedSceneGraphProjectState(overrides = {}) {
  const clipPath = '/tmp/cut/shot-a.mov';
  const sceneId = 'scene_01';
  const takeNodeId = 'take_01_a';
  const sceneNodeId = 'scene_node_01';
  const noteNodeId = 'note_01';

  return {
    success: true,
    schema_version: 'cut_project_state_v1',
    project: {
      project_id: 'cut-scene-graph-loaded',
      display_name: 'CUT Scene Graph Loaded Fixture',
      source_path: clipPath,
      sandbox_root: '/tmp/cut-scene-graph-loaded',
      state: 'ready',
    },
    bootstrap_state: { project_id: 'cut-scene-graph-loaded', last_stats: { fixture: 'scene_graph_loaded' } },
    runtime_ready: true,
    graph_ready: true,
    waveform_ready: true,
    transcript_ready: true,
    thumbnail_ready: true,
    audio_sync_ready: true,
    slice_ready: true,
    timecode_sync_ready: true,
    sync_surface_ready: true,
    meta_sync_ready: false,
    time_markers_ready: true,
    timeline_state: {
      schema_version: 'cut_timeline_state_v1',
      timeline_id: 'main',
      selection: { clip_ids: ['clip_a'], scene_ids: [sceneId] },
      lanes: [
        {
          lane_id: 'video_main',
          lane_type: 'video_main',
          clips: [
            {
              clip_id: 'clip_a',
              scene_id: sceneId,
              start_sec: 0,
              duration_sec: 4.2,
              source_path: clipPath,
              sync: {
                method: 'waveform',
                offset_sec: 0.18,
                confidence: 0.94,
                reference_path: '/tmp/cut/master.wav',
              },
            },
          ],
        },
      ],
    },
    scene_graph: {
      schema_version: 'cut_scene_graph_v1',
      graph_id: 'main',
      nodes: [
        { node_id: sceneNodeId, node_type: 'scene', label: 'Opening Scene', metadata: { scene_index: 1, summary: 'Open on the establishing beat.' } },
        { node_id: takeNodeId, node_type: 'take', label: 'Take A', metadata: { take_index: 1, summary: 'Primary timing candidate.' } },
        { node_id: noteNodeId, node_type: 'note', label: 'Director Note', metadata: { summary: 'Hold for reaction before cut.' } },
      ],
      edges: [
        { edge_id: 'edge_contains', edge_type: 'contains', source: sceneNodeId, target: takeNodeId, weight: 1 },
        { edge_id: 'edge_semantic', edge_type: 'semantic_match', source: takeNodeId, target: noteNodeId, weight: 0.66 },
      ],
    },
    scene_graph_view: {
      schema_version: 'cut_scene_graph_view_v1',
      graph_id: 'main',
      generated_at: '2026-03-12T17:35:00Z',
      nodes: [
        {
          node_id: sceneNodeId,
          node_type: 'scene',
          visual_bucket: 'primary_structural',
          label: 'Opening Scene',
          parent_id: null,
          rank_hint: 1,
          selection_refs: { clip_ids: ['clip_a'], scene_ids: [sceneId], source_paths: [clipPath] },
          render_hints: {
            display_mode: 'scene_card',
            poster_url: POSTER_DATA_URL,
            modality: 'video',
            duration_sec: 4.2,
            marker_count: 2,
            sync_badge: 'waveform',
          },
          metadata: { summary: 'Open on the establishing beat.' },
        },
        {
          node_id: takeNodeId,
          node_type: 'take',
          visual_bucket: 'selected_shot',
          label: 'Take A',
          parent_id: sceneNodeId,
          rank_hint: 2,
          selection_refs: { clip_ids: ['clip_a'], scene_ids: [sceneId], source_paths: [clipPath] },
          render_hints: {
            display_mode: 'take_preview',
            poster_url: POSTER_DATA_URL,
            modality: 'video',
            duration_sec: 4.2,
            marker_count: 3,
            sync_badge: 'waveform',
          },
          metadata: { summary: 'Primary timing candidate.' },
        },
        {
          node_id: noteNodeId,
          node_type: 'note',
          visual_bucket: 'intel_overlay',
          label: 'Director Note',
          parent_id: takeNodeId,
          rank_hint: 3,
          selection_refs: { clip_ids: ['clip_a'], scene_ids: [sceneId], source_paths: [clipPath] },
          render_hints: {
            display_mode: 'note_chip',
            poster_url: null,
            modality: 'text',
            duration_sec: null,
            marker_count: 0,
            sync_badge: null,
          },
          metadata: { summary: 'Hold for reaction before cut.' },
        },
      ],
      edges: [
        { edge_id: 'edge_contains', edge_type: 'contains', family: 'structural', source: sceneNodeId, target: takeNodeId, weight: 1, visible_by_default: true },
        { edge_id: 'edge_semantic', edge_type: 'semantic_match', family: 'intelligence', source: takeNodeId, target: noteNodeId, weight: 0.66, visible_by_default: true },
      ],
      focus: {
        selected_clip_ids: ['clip_a'],
        selected_scene_ids: [sceneId],
        focused_node_ids: [sceneNodeId, takeNodeId],
        anchor_node_id: takeNodeId,
      },
      layout_hints: {
        structural_edge_types: ['contains', 'follows'],
        intelligence_edge_types: ['semantic_match'],
        primary_rank_edge_types: ['contains', 'follows'],
      },
      crosslinks: {
        by_clip_id: { clip_a: [takeNodeId, sceneNodeId] },
        by_scene_id: { [sceneId]: [sceneNodeId, takeNodeId] },
        by_source_path: { [clipPath]: [takeNodeId, sceneNodeId, noteNodeId] },
      },
      structural_subgraph: {
        node_ids: [sceneNodeId, takeNodeId],
        edge_ids: ['edge_contains'],
      },
      overlay_edges: [
        { edge_id: 'edge_semantic', edge_type: 'semantic_match', family: 'intelligence', source: takeNodeId, target: noteNodeId, weight: 0.66, visible_by_default: true },
      ],
      dag_projection: {
        root_ids: ['cut_graph:scene_node_01'],
        nodes: [
          {
            id: 'cut_graph:scene_node_01',
            type: 'roadmap_task',
            label: 'Opening Scene',
            status: 'active',
            layer: 0,
            parentId: null,
            taskId: 'scene_node_01',
            graphKind: 'project_task',
            primaryNodeId: sceneNodeId,
            metadata: { visualBucket: 'primary_structural' },
          },
          {
            id: 'cut_graph:take_01_a',
            type: 'roadmap_task',
            label: 'Take A',
            status: 'active',
            layer: 1,
            parentId: 'cut_graph:scene_node_01',
            taskId: 'take_01_a',
            graphKind: 'project_task',
            primaryNodeId: takeNodeId,
            metadata: { visualBucket: 'selected_shot' },
          },
          {
            id: 'cut_graph:note_01',
            type: 'note',
            label: 'Director Note',
            status: 'idle',
            layer: 2,
            parentId: 'cut_graph:take_01_a',
            taskId: 'note_01',
            graphKind: 'project_task',
            primaryNodeId: noteNodeId,
            metadata: { visualBucket: 'intel_overlay' },
          },
        ],
        edges: [
          { id: 'edge_contains', source: 'cut_graph:scene_node_01', target: 'cut_graph:take_01_a', type: 'structural', strength: 1, relationKind: 'contains' },
          { id: 'edge_semantic', source: 'cut_graph:take_01_a', target: 'cut_graph:note_01', type: 'semantic', strength: 0.66, relationKind: 'semantic_match' },
        ],
      },
      inspector: {
        primary_node_id: takeNodeId,
        focused_nodes: [
          {
            node_id: sceneNodeId,
            node_type: 'scene',
            label: 'Opening Scene',
            summary: 'Open on the establishing beat.',
            related_clip_ids: ['clip_a'],
            related_source_paths: [clipPath],
          },
          {
            node_id: takeNodeId,
            node_type: 'take',
            label: 'Take A',
            summary: 'Primary timing candidate.',
            related_clip_ids: ['clip_a'],
            related_source_paths: [clipPath],
          },
        ],
      },
    },
    waveform_bundle: { items: [{ item_id: 'wf_a', source_path: clipPath, waveform_bins: [0.2, 0.7, 0.5, 0.9] }] },
    transcript_bundle: { items: [{ item_id: 'tr_a', source_path: clipPath, text: 'Open on the establishing beat.', segments: [{ start: 0, end: 1.2, text: 'Open on the establishing beat.' }] }] },
    thumbnail_bundle: { items: [{ item_id: 'thumb_a', source_path: clipPath, modality: 'video', duration_sec: 4.2, poster_url: POSTER_DATA_URL }] },
    audio_sync_result: {
      items: [
        {
          item_id: 'as_a',
          source_path: clipPath,
          reference_path: '/tmp/cut/master.wav',
          method: 'waveform',
          detected_offset_sec: 0.18,
          confidence: 0.94,
        },
      ],
    },
    slice_bundle: { items: [{ item_id: 'slice_a', source_path: clipPath, start_sec: 0.6, end_sec: 1.8, score: 0.88 }] },
    timecode_sync_result: {
      items: [
        {
          item_id: 'tc_a',
          source_path: clipPath,
          reference_path: '/tmp/cut/master.wav',
          reference_timecode: '01:00:00:00',
          source_timecode: '01:00:00:00',
          detected_offset_sec: 0,
          method: 'timecode',
          confidence: 1,
        },
      ],
    },
    sync_surface: {
      schema_version: 'cut_sync_surface_v1',
      items: [{ item_id: 'sync_surface_a', source_path: clipPath, recommended_method: 'waveform', recommended_offset_sec: 0.18, confidence: 0.94 }],
    },
    time_marker_bundle: { items: [{ marker_id: 'marker_a', kind: 'favorite', media_path: clipPath, start_sec: 0.5, end_sec: 1.2, status: 'active', score: 1 }] },
    recent_jobs: [],
    active_jobs: [],
    ...overrides,
  };
}

module.exports = {
  POSTER_DATA_URL,
  createLoadedSceneGraphProjectState,
};
