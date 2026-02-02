/**
 * Core WebSocket hook for real-time communication with VETKA backend.
 * Handles tree updates, chat streaming, group messages, search, and file events.
 *
 * @status active
 * @phase 96
 * @depends socket.io-client, zustand, chatTreeStore
 * @used_by App, ChatPanel, TreeViewer, SearchPanel
 */

import { useEffect, useRef, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { useStore, TreeNode, AgentMessage, CameraCommand } from '../store/useStore';
import { useChatTreeStore } from '../store/chatTreeStore';
import { calculateSimpleLayout } from '../utils/layout';
import {
  convertApiResponse,
  convertLegacyNode,
  VetkaApiResponse,
  LegacyApiNode,
} from '../utils/apiConverter';
import type { ChatMessage, WorkflowStatus, WorkflowResult, AgentChunk } from '../types/chat';
import { getSocketUrl, API_BASE } from '../config/api.config';
// Phase 70: Viewport context for AI spatial awareness
import { buildViewportContext, ViewportContext } from '../utils/viewport';

// FIX_95.9.6: Camera debounce for multiple rapid file changes
// Problem: When many files change quickly, camera flies back and forth causing confusion
// Solution: Debounce with highlight-only mode for rapid changes
let lastCameraFocusTime = 0;
let pendingCameraFiles: string[] = [];
const CAMERA_DEBOUNCE_MS = 2000;  // Minimum time between camera fly-tos
const RAPID_CHANGE_THRESHOLD = 3; // If >3 files in debounce window, only highlight

// Use dynamic socket URL from config
const SOCKET_URL = getSocketUrl();

interface ServerToClientEvents {
  connect: () => void;
  disconnect: () => void;
  error: (data: any) => void;
  connect_error: (error: Error) => void;
  tree_updated: (data: { nodes: any[]; edges?: any[]; tree?: any }) => void;
  node_added: (data: { path: string; node?: any; event?: any }) => void;
  node_removed: (data: { path: string; event?: any }) => void;
  node_updated: (data: { path: string; event?: any }) => void;
  tree_bulk_update: (data: { path: string; count: number; events: string[] }) => void;
  node_moved: (data: { path: string; position: { x: number; y: number; z: number } }) => void;
  layout_changed: (data: { positions: Record<string, { x: number; y: number; z: number }> }) => void;
  // Phase 54.4: Browser folder events
  browser_folder_added: (data: { root_name: string; files_count: number; indexed_count: number; virtual_path: string }) => void;
  // Phase 54.9: Server directory scanned
  directory_scanned: (data: { path: string; files_count: number; root_name: string }) => void;
  agent_message: (data: {
    agent: string;
    content: string;
    artifacts?: Array<{ name: string; content: string; type: string; language?: string }>;
    context?: { selected_file?: string };
    source_files?: string[];
  }) => void;
  scan_progress: (data: { progress: number; status: string }) => void;
  scan_complete: (data: { nodes_count: number }) => void;
  camera_control: (data: { action: string; target: string; zoom: string; highlight: boolean }) => void;
  file_highlighted: (data: { path: string }) => void;
  file_unhighlighted: (data: { path: string }) => void;
  // Chat events
  workflow_status: (data: WorkflowStatus) => void;
  workflow_result: (data: WorkflowResult) => void;
  agent_chunk: (data: AgentChunk) => void;
  chat_response: (data: {
    message: string;
    agent?: string;
    model?: string;
    workflow_id?: string;
  }) => void;
  // Phase 46: Streaming events
  stream_start: (data: { id: string; agent: string; model: string }) => void;
  stream_token: (data: { id: string; token: string }) => void;
  stream_end: (data: {
    id: string;
    full_message: string;
    metadata: { tokens_output: number; tokens_input: number; model: string; agent: string };
  }) => void;
  // === PHASE 55: APPROVAL EVENTS ===
  approval_required: (data: {
    id: string;
    workflow_id: string;
    artifacts: any[];
    eval_score: number;
    eval_feedback: string;
    status: string;
    created_at: string;
  }) => void;
  approval_decided: (data: {
    request_id: string;
    status: 'approved' | 'rejected';
    reason: string;
  }) => void;
  approval_error: (data: {
    request_id: string;
    error: string;
  }) => void;
  // === PHASE 56: GROUP EVENTS ===
  group_created: (data: {
    id: string;
    name: string;
    admin_id: string;
    participants: Record<string, any>;
  }) => void;
  group_joined: (data: {
    group_id: string;
    participant: any;
  }) => void;
  group_left: (data: {
    group_id: string;
    agent_id: string;
  }) => void;
  group_participant_updated: (data: {
    group_id: string;
    agent_id: string;
    model_id: string;
  }) => void;
  group_message: (data: {
    id: string;
    group_id: string;
    sender_id: string;
    content: string;
    mentions: string[];
    message_type: string;
    created_at: string;
  }) => void;
  group_typing: (data: {
    group_id: string;
    agent_id: string;
  }) => void;
  // Phase 57: Group streaming events
  group_stream_start: (data: {
    id: string;
    group_id: string;
    agent_id: string;
    model: string;
  }) => void;
  group_stream_token: (data: {
    id: string;
    group_id: string;
    agent_id: string;
    token: string;
  }) => void;
  group_stream_end: (data: {
    id: string;
    group_id: string;
    agent_id: string;
    full_message: string;
    metadata?: { tokens_output: number; model: string };
    error?: string;
  }) => void;
  group_error: (data: {
    error: string;
  }) => void;
  // Phase 80.18: Socket room join acknowledgment
  group_joined_ack: (data: {
    group_id: string;
    room?: string;
  }) => void;
  agent_response: (data: {
    agent_id: string;
    content: string;
    status: string;
  }) => void;
  task_created: (data: {
    id: string;
    group_id: string;
    assigned_to: string;
    description: string;
    status: string;
  }) => void;
  // Model registry
  model_status: (data: {
    model_id: string;
    available: boolean;
  }) => void;
  // === PHASE 103.6: ARTIFACT STAGING EVENTS ===
  artifacts_staged: (data: {
    group_id: string;
    agent: string;
    count: number;
    task_ids: string[];
    qa_score: number;
  }) => void;
  artifacts_applied: (data: {
    group_id: string;
    task_ids: string[];
    files: string[];
    success: boolean;
  }) => void;
  // === PHASE 103.7: CHAT PERSISTENCE EVENTS ===
  message_saved: (data: {
    group_id: string;
    message_id: string;
    success: boolean;
  }) => void;
  chat_history_loaded: (data: {
    group_id: string;
    message_count: number;
    messages: Array<{
      id: string;
      role: string;
      content: string;
      sender_id: string;
      timestamp: string;
    }>;
  }) => void;
  // === PHASE 104.8: VOICE & ROOM EVENTS ===
  voice_transcript: (data: {
    text: string;
    is_final: boolean;
    confidence?: number;
    language?: string;
    timestamp?: string;
  }) => void;
  // === PHASE 104.9: ARTIFACT APPROVAL EVENTS ===
  // MARKER_104_VISUAL - L2 edit capability event
  artifact_approval: (data: {
    artifactId: string;
    approvalLevel: 'L1' | 'L2' | 'L3';
    action?: 'approve' | 'reject' | 'edit';
    content?: string;
    reason?: string;
  }) => void;
  jarvis_interrupt: (data: {
    priority: number;
    reason?: string;
    timestamp?: string;
  }) => void;
  jarvis_prediction: (data: {
    predictions: string[];
    context?: string;
    confidence?: number;
  }) => void;
  stream_error: (data: {
    error: string;
    stream_id?: string;
    code?: string;
  }) => void;
  room_joined: (data: {
    room_id: string;
    user_id?: string;
    participants?: string[];
  }) => void;
  room_left: (data: {
    room_id: string;
    user_id?: string;
    reason?: string;
  }) => void;
  // === PHASE 56.5: CHAT-AS-TREE EVENTS ===
  chat_node_created: (data: {
    chatId: string;
    parentId: string;
    name: string;
    participants: string[];
  }) => void;
  chat_node_updated: (data: {
    chatId: string;
    messageCount: number;
    preview?: string;
  }) => void;
  // MARKER_108_3_SOCKETIO_UPDATE: Phase 108.3 - Real-time chat node opacity updates
  chat_node_update: (data: {
    chat_id: string;
    decay_factor: number;
    last_activity: string;
    message_count?: number;
  }) => void;
  artifact_placeholder: (data: {
    artifactId: string;
    chatId: string;
    name: string;
    artifactType: string;
  }) => void;
  artifact_stream: (data: {
    artifactId: string;
    progress: number;
  }) => void;
  artifact_complete: (data: {
    artifactId: string;
    preview?: string;
  }) => void;
  hostess_memory_tree: (data: {
    nodes: Array<{
      id: string;
      label: string;
      size: number;
      opacity: number;
    }>;
  }) => void;
  // Phase 57.8: Artifact tree node event
  artifact_tree_node: (data: {
    id: string;
    name: string;
    type: 'artifact';
    artifact_type: string;
    parent_id: string;
    created_by: string;
    preview: string;
    language: string;
    size: number;
  }) => void;
  // Phase 57.9: API Key learning events
  key_saved: (data: {
    provider: string;
    display_name: string;
    confidence: number;
    message: string;
  }) => void;
  key_learned: (data: {
    provider: string;
    display_name: string;
    success: boolean;
    message: string;
  }) => void;
  unknown_key_type: (data: {
    key_preview: string;
    analysis: {
      prefix: string | null;
      length: number;
      charset: string;
      separator: string | null;
    };
    message: string;
  }) => void;
  key_status: (data: {
    providers: Record<string, { count: number; active: boolean; learned?: boolean }>;
    providers_with_keys: string[];
    total: number;
    active: number;
  }) => void;
  key_error: (data: {
    error: string;
  }) => void;
  // === PHASE 68: SEARCH EVENTS ===
  search_results: (data: {
    results: Array<{
      id: string;
      name: string;
      path: string;
      type: string;
      relevance: number;
      preview?: string;
      source?: string;
    }>;
    total: number;
    query: string;
    took_ms: number;
    mode?: string;
    sources?: string[];
  }) => void;
  search_error: (data: {
    error: string;
    query: string;
  }) => void;
  // Phase 69: Multi-highlight event from search results
  highlight_nodes: (data: {
    nodeIds: string[];
  }) => void;
}

// Phase 61: Pinned file type
interface PinnedFile {
  id: string;
  path: string;
  name: string;
  type: string;
}

interface ClientToServerEvents {
  request_tree: () => void;
  move_node: (data: { path: string; position: { x: number; y: number; z: number } }) => void;
  select_node: (data: { path: string }) => void;
  // Phase 70: Added viewport_context for AI spatial awareness
  user_message: (data: { text: string; node_path: string; node_id: string; model?: string; pinned_files?: PinnedFile[]; viewport_context?: ViewportContext }) => void;
  // === PHASE 55: APPROVAL ACTIONS ===
  approve_artifact: (data: { request_id: string; reason?: string }) => void;
  reject_artifact: (data: { request_id: string; reason: string }) => void;
  // === PHASE 56: GROUP ACTIONS ===
  join_group: (data: { group_id: string }) => void;
  leave_group: (data: { group_id: string }) => void;
  group_message: (data: { group_id: string; sender_id: string; content: string }) => void;
  group_typing: (data: { group_id: string; agent_id: string }) => void;
  // === PHASE 56.5: CHAT-AS-TREE ACTIONS ===
  create_chat_node: (data: {
    chatId: string;
    parentId: string;
    name: string;
    participants: string[];
  }) => void;
  get_hostess_memory: (data?: {}) => void;
  // === PHASE 57.9: API KEY ACTIONS ===
  add_api_key: (data: { key: string }) => void;
  learn_key_type: (data: { key: string; provider: string }) => void;
  get_key_status: (data?: { provider?: string }) => void;
  // === PHASE 68: SEARCH ACTIONS ===
  search_query: (data: {
    text: string;
    limit?: number;
    mode?: 'hybrid' | 'semantic' | 'keyword' | 'filename';
    filters?: Record<string, unknown>;
    min_score?: number;
  }) => void;
}

export function useSocket() {
  const socketRef = useRef<Socket<ServerToClientEvents, ClientToServerEvents> | null>(null);
  const tokenBufferRef = useRef<Map<string, string>>(new Map());
  const rafIdRef = useRef<number | null>(null);

  const setNodes = useStore((state) => state.setNodes);
  const setNodesFromRecord = useStore((state) => state.setNodesFromRecord);
  const setEdges = useStore((state) => state.setEdges);
  const updateNodePosition = useStore((state) => state.updateNodePosition);
  const setError = useStore((state) => state.setError);
  const setSocketConnected = useStore((state) => state.setSocketConnected);
  const isSocketConnected = useStore((state) => state.isSocketConnected);
  const addMessage = useStore((state) => state.addMessage);
  const setCameraCommand = useStore((state) => state.setCameraCommand);
  const highlightNode = useStore((state) => state.highlightNode);
  const addChatMessage = useStore((state) => state.addChatMessage);
  const setWorkflowStatus = useStore((state) => state.setWorkflowStatus);
  const appendStreamingContent = useStore((state) => state.appendStreamingContent);
  const setIsTyping = useStore((state) => state.setIsTyping);

  // Phase 49.2: Batch token updates with requestAnimationFrame
  const flushTokenBuffer = useCallback(() => {
    if (tokenBufferRef.current.size === 0) return;

    useStore.setState((state) => {
      const updated = [...state.chatMessages];
      tokenBufferRef.current.forEach((tokens, msgId) => {
        const idx = updated.findIndex((m) => m.id === msgId);
        if (idx !== -1) {
          updated[idx] = {
            ...updated[idx],
            content: updated[idx].content + tokens,
          };
        }
      });
      tokenBufferRef.current.clear();
      return { chatMessages: updated };
    });

    rafIdRef.current = null;
  }, []);

  // Helper function to reload tree data via HTTP
  const reloadTreeFromHttp = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/tree/data`);
      if (response.ok) {
        const treeData = await response.json();
        console.log('[Socket] Tree reloaded via HTTP:', treeData.tree?.nodes?.length, 'nodes');

        if (treeData.tree) {
          const vetkaResponse: VetkaApiResponse = {
            tree: {
              nodes: treeData.tree.nodes,
              edges: treeData.tree.edges || [],
            },
          };
          const { nodes: convertedNodes, edges } = convertApiResponse(vetkaResponse);
          setNodesFromRecord(convertedNodes);
          setEdges(edges);
        }
      }
    } catch (err) {
      console.error('[Socket] Tree reload error:', err);
    }
  }, [setNodesFromRecord, setEdges]);

  useEffect(() => {
    const socket: Socket<ServerToClientEvents, ClientToServerEvents> = io(SOCKET_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      // console.log('[Socket] Connected to', SOCKET_URL);
      setSocketConnected(true);
      setError(null);
      socket.emit('request_tree');
    });

    socket.on('disconnect', () => {
      // console.log('[Socket] Disconnected');
      setSocketConnected(false);
    });

    socket.on('connect_error', (error) => {
      // console.warn('[Socket] Connection error:', error.message);
      setSocketConnected(false);
    });

    socket.on('tree_updated', (data) => {
      // console.log('[Socket] tree_updated:', data.nodes?.length || data.tree?.nodes?.length, 'nodes');

      // Check for new VETKA format
      if (data.tree) {
        const vetkaResponse: VetkaApiResponse = {
          tree: {
            nodes: data.tree.nodes,
            edges: data.tree.edges || [],
          },
        };
        const { nodes: convertedNodes, edges } = convertApiResponse(vetkaResponse);
        setNodesFromRecord(convertedNodes);
        setEdges(edges);
        return;
      }

      // Legacy format
      if (data.nodes) {
        const treeNodes: TreeNode[] = data.nodes.map((n: LegacyApiNode) =>
          convertLegacyNode(n)
        );
        const positioned = calculateSimpleLayout(treeNodes);
        setNodes(positioned);
      }
    });

    // Phase 80.24: Watchdog socket listeners - enhanced with detailed logging
    // Phase 90.11: Added camera focus after indexing completes
    socket.on('node_added', async (data) => {
      console.log('[Socket] node_added received:', {
        path: data.path,
        event: data.event,
        indexed: data.indexed,
        timestamp: new Date().toISOString()
      });

      // Trigger tree refetch via HTTP to get updated tree with proper positions
      await reloadTreeFromHttp();

      // FIX_95.9.6: Camera debounce for rapid file changes
      // Problem: Multiple files changing = camera flies everywhere = CPU heat + confusion
      // Solution: Track pending files, debounce fly-to, use highlight-only for bursts
      const fileName = data.path.split('/').pop() || data.path;
      const now = Date.now();

      // Track this file in pending list
      pendingCameraFiles.push(fileName);

      // Clean old entries (older than debounce window)
      pendingCameraFiles = pendingCameraFiles.filter(
        (_, i) => i >= pendingCameraFiles.length - 10  // Keep last 10 max
      );

      const timeSinceLastFocus = now - lastCameraFocusTime;
      const tooManyFiles = pendingCameraFiles.length >= RAPID_CHANGE_THRESHOLD;

      setTimeout(() => {
        if (tooManyFiles && timeSinceLastFocus < CAMERA_DEBOUNCE_MS) {
          // Too many rapid changes - just highlight without fly-to
          setCameraCommand({
            target: fileName,
            zoom: 'none',      // Don't change zoom
            highlight: true,   // Just highlight the node
          });
          console.log('[Socket] ⚡ Rapid changes detected, highlight-only:', fileName, `(${pendingCameraFiles.length} files in window)`);
        } else {
          // Normal case - fly to new file
          setCameraCommand({
            target: fileName,
            zoom: 'medium',
            highlight: true,
          });
          lastCameraFocusTime = Date.now();
          pendingCameraFiles = [];  // Reset after fly-to
          console.log('[Socket] ✅ Camera focusing on new file:', fileName);
        }
      }, 800);
    });

    socket.on('node_removed', (data) => {
      console.log('[Socket] node_removed received:', {
        path: data.path,
        event: data.event,
        timestamp: new Date().toISOString()
      });
      // Remove node from local state
      const { removeNode } = useStore.getState();
      removeNode(data.path);
    });

    socket.on('node_updated', (data) => {
      console.log('[Socket] node_updated received:', {
        path: data.path,
        event: data.event,
        timestamp: new Date().toISOString()
      });
      // Trigger tree refetch for updated node
      reloadTreeFromHttp();
    });

    socket.on('tree_bulk_update', (data) => {
      console.log('[Socket] tree_bulk_update received:', {
        path: data.path,
        count: data.count,
        events: data.events,
        timestamp: new Date().toISOString()
      });
      // Reload entire tree for bulk updates (git checkout, etc.)
      reloadTreeFromHttp();
    });

    socket.on('node_moved', (data) => {
      // console.log('[Socket] node_moved:', data.path);
      updateNodePosition(data.path, data.position);
    });

    socket.on('layout_changed', (data) => {
      // console.log('[Socket] layout_changed');
      Object.entries(data.positions).forEach(([path, pos]) => {
        updateNodePosition(path, pos);
      });
    });

    socket.on('agent_message', (data) => {
      // console.log('[Socket] agent_message:', data.agent, data.content.slice(0, 50));

      const message: AgentMessage = {
        id: `msg_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
        agent: data.agent,
        content: data.content,
        timestamp: Date.now(),
        artifacts: data.artifacts,
        sourceFiles: data.source_files,
      };

      addMessage(message);
    });

    socket.on('camera_control', (data) => {
      // console.log('[Socket] camera_control:', data.target, data.zoom);

      if (data.action === 'focus') {
        const command: CameraCommand = {
          target: data.target,
          zoom: data.zoom as 'close' | 'medium' | 'far',
          highlight: data.highlight,
        };
        setCameraCommand(command);
      }
    });

    socket.on('file_highlighted', (data) => {
      // console.log('[Socket] file_highlighted:', data.path);
      highlightNode(data.path);
    });

    socket.on('file_unhighlighted', (data) => {
      // console.log('[Socket] file_unhighlighted:', data.path);
      highlightNode(null);
    });

    // Phase 92: Dispatch scan events to window for ScanProgressPanel
    socket.on('scan_progress', (data) => {
      // console.log('[Socket] scan_progress:', data.progress, '%', data.status);
      if (typeof window !== 'undefined') {
        // Normalize data - backend sends {current, indexed}, frontend expects {progress, status, file_path}
        // Phase 92.4: Added file_size and file_mtime for inline display
        const normalizedData = {
          progress: typeof data.progress === 'number' ? data.progress :
            (data.current && data.total ? Math.round((data.current / data.total) * 100) : 0),
          status: data.status || 'scanning',
          file_path: data.file_path || data.path,
          current: data.current,
          total: data.total,
          file_size: data.file_size,
          file_mtime: data.file_mtime,
        };
        window.dispatchEvent(
          new CustomEvent('scan_progress', { detail: normalizedData })
        );
      }
    });

    socket.on('scan_complete', (data) => {
      // console.log('[Socket] scan_complete:', data.nodes_count, 'nodes');
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('scan_complete', { detail: data })
        );
      }
    });

    // Phase 54.5: Browser folder added - reload tree via HTTP to get files with proper Sugiyama positions
    socket.on('browser_folder_added', async (data) => {
      // console.log('[Socket] browser_folder_added:', data.root_name, data.files_count, 'files');

      // Fetch fresh tree data via HTTP (socket request_tree handler doesn't exist on backend)
      try {
        const response = await fetch('/api/tree/data');
        if (response.ok) {
          const treeData = await response.json();
          // console.log('[Socket] Tree reloaded via HTTP:', treeData.tree?.nodes?.length, 'nodes');

          if (treeData.tree) {
            const vetkaResponse: VetkaApiResponse = {
              tree: {
                nodes: treeData.tree.nodes,
                edges: treeData.tree.edges || [],
              },
            };
            const { nodes: convertedNodes, edges } = convertApiResponse(vetkaResponse);
            setNodesFromRecord(convertedNodes);
            setEdges(edges);

            // Camera fly-to after tree is loaded
            setTimeout(() => {
              setCameraCommand({
                target: data.root_name,
                zoom: 'medium',
                highlight: true,
              });
            }, 300);
          }
        }
      } catch (err) {
        console.error('[Socket] Tree reload error:', err);
      }
    });

    // Phase 54.9: Server directory scanned
    // Phase 92: Also dispatch to window for ScanProgressPanel
    socket.on('directory_scanned', async (data) => {
      // console.log('[Socket] directory_scanned:', data.path, data.files_count, 'files');

      // Phase 92: Dispatch to window for ScanProgressPanel
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('directory_scanned', { detail: data })
        );
      }

      try {
        // Reload tree data via HTTP (use API_BASE from config)
        const response = await fetch(`${API_BASE}/tree/data`);
        if (response.ok) {
          const treeData = await response.json();
          // console.log('[Socket] Tree reloaded after directory scan:', treeData.tree?.nodes?.length, 'nodes');

          if (treeData.tree) {
            const vetkaResponse: VetkaApiResponse = {
              tree: {
                nodes: treeData.tree.nodes,
                edges: treeData.tree.edges || [],
              },
            };
            const { nodes: convertedNodes, edges } = convertApiResponse(vetkaResponse);
            setNodesFromRecord(convertedNodes);
            setEdges(edges);

            // Camera fly-to the new folder
            setTimeout(() => {
              if (data.root_name) {
                setCameraCommand({
                  target: data.root_name,
                  zoom: 'medium',
                  highlight: true,
                });
              }
            }, 300);
          }
        }
      } catch (err) {
        console.error('[Socket] Error handling directory_scanned:', err);
      }
    });

    // Chat events
    socket.on('workflow_status', (data) => {
      // console.log('[Socket] workflow_status:', data.step, data.status);
      setWorkflowStatus(data);
      setIsTyping(data.status === 'running');
    });

    socket.on('workflow_result', (data) => {
      // console.log('[Socket] workflow_result RAW:', JSON.stringify(data, null, 2).slice(0, 500));

      // Phase 27.12: Enhanced workflow result handling
      const message: ChatMessage = {
        id: crypto.randomUUID(),
        workflow_id: data.workflow_id,
        role: 'assistant',
        content: data.feature || data.result || data.message || 'Workflow completed',
        type: 'compound',
        timestamp: new Date().toISOString(),
        sections: {
          pm_plan: data.pm_plan,
          architecture: data.architecture,
          implementation: data.implementation,
          tests: data.tests,
        },
        metadata: {
          duration: data.duration,
          model: data.model,
          score: data.score || data.eval_score,
        },
      };

      addChatMessage(message);
      setWorkflowStatus(null);
      setIsTyping(false);
    });

    socket.on('chat_response', (data) => {
      // console.log('[Socket] chat_response:', data.agent || 'assistant');

      const message: ChatMessage = {
        id: crypto.randomUUID(),
        workflow_id: data.workflow_id,
        role: 'assistant',
        agent: data.agent as ChatMessage['agent'],
        content: data.message,
        type: 'text',
        timestamp: new Date().toISOString(),
        metadata: { model: data.model },
      };

      addChatMessage(message);
      setIsTyping(false);
    });

    socket.on('agent_chunk', (data) => {
      // For future streaming support
      appendStreamingContent(data.delta);
    });

    // Phase 46: Streaming events
    socket.on('stream_start', (data) => {
      // console.log('[Stream] Started:', data);
      setIsTyping(true);

      // Create placeholder message for streaming
      const streamingMessage: ChatMessage = {
        id: data.id,
        role: 'assistant',
        agent: data.agent as ChatMessage['agent'],
        content: '',
        type: 'text',
        timestamp: new Date().toISOString(),
        metadata: { model: data.model, isStreaming: true },
      };
      addChatMessage(streamingMessage);
    });

    socket.on('stream_token', (data) => {
      // Phase 49.2: Batch token updates with requestAnimationFrame
      // Accumulate tokens in buffer and flush once per frame (~16ms)
      const current = tokenBufferRef.current.get(data.id) || '';
      tokenBufferRef.current.set(data.id, current + data.token);

      // Schedule flush if not already scheduled
      if (!rafIdRef.current) {
        rafIdRef.current = requestAnimationFrame(() => {
          flushTokenBuffer();
        });
      }
    });

    socket.on('stream_end', (data) => {
      // console.log('[Stream] Complete:', data.metadata);
      setIsTyping(false);

      // Finalize streaming message with metadata
      useStore.setState((state) => ({
        chatMessages: state.chatMessages.map((msg) =>
          msg.id === data.id
            ? {
                ...msg,
                content: data.full_message,
                metadata: {
                  ...msg.metadata,
                  isStreaming: false,
                  tokens_output: data.metadata.tokens_output,
                  tokens_input: data.metadata.tokens_input,
                },
              }
            : msg
        ),
      }));
    });

    // === PHASE 55: APPROVAL LISTENERS ===

    socket.on('approval_required', (data) => {
      // console.log('[Socket] Approval required:', data.id);

      // Dispatch custom event for UI to show approval modal
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('approval-required', {
            detail: data,
          })
        );
      }
    });

    socket.on('approval_decided', (data) => {
      // console.log('[Socket] Approval decided:', data.request_id, data.status);

      // Dispatch custom event for UI to update
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('approval-decided', {
            detail: data,
          })
        );
      }
    });

    socket.on('approval_error', (data) => {
      console.error('[Socket] Approval error:', data.request_id, data.error);

      // Dispatch custom event for UI error handling
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('approval-error', {
            detail: data,
          })
        );
      }
    });

    // === PHASE 56.2: GROUP CHAT LISTENERS ===

    socket.on('group_created', (data) => {
      // console.log('[Socket] Group created:', data.name, data.id);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('group-created', { detail: data })
        );
      }
    });

    socket.on('group_joined', (data) => {
      // console.log('[Socket] Agent joined group:', data.participant.agent_id);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('group-joined', { detail: data })
        );
      }
    });

    socket.on('group_left', (data) => {
      // console.log('[Socket] Agent left group:', data.agent_id);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('group-left', { detail: data })
        );
      }
    });

    // MARKER_103_GC4: Missing handler - Phase 103
    socket.on('group_participant_updated', (data) => {
      console.log('[Socket] Participant updated:', data.agent_id, data.model_id);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('group-participant-updated', { detail: data })
        );
      }
    });

    socket.on('group_message', (data) => {
      // console.log('[Socket] Group message:', data.sender_id, data.content.slice(0, 50));
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('group-message', { detail: data })
        );
      }
    });

    socket.on('group_typing', (data) => {
      // console.log('[Socket] Agent typing:', data.agent_id);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('group-typing', { detail: data })
        );
      }
    });

    // Phase 57: Group streaming listeners
    socket.on('group_stream_start', (data) => {
      // console.log('[Socket] Group stream start:', data.agent_id, data.model);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('group-stream-start', { detail: data })
        );
      }
    });

    socket.on('group_stream_token', (data) => {
      // Don't log each token - too noisy
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('group-stream-token', { detail: data })
        );
      }
    });

    socket.on('group_stream_end', (data) => {
      // console.log('[Socket] Group stream end:', data.agent_id, data.full_message?.length || 0, 'chars');
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('group-stream-end', { detail: data })
        );
      }
    });

    socket.on('group_error', (data) => {
      console.error('[Socket] Group error:', data.error);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('group-error', { detail: data })
        );
      }
    });

    // Phase 80.18: Socket room join acknowledgment - fixes race condition
    socket.on('group_joined_ack', (data) => {
      console.log('[Socket] group_joined_ack:', data.group_id);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('group_joined_ack', { detail: data })
        );
      }
    });

    socket.on('agent_response', (data) => {
      // console.log('[Socket] Agent response:', data.agent_id, data.content.slice(0, 50));
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('agent-response', { detail: data })
        );
      }
    });

    socket.on('task_created', (data) => {
      // console.log('[Socket] Task created:', data.description);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('task-created', { detail: data })
        );
      }
    });

    socket.on('model_status', (data) => {
      // console.log('[Socket] Model status:', data.model_id, data.available ? 'online' : 'offline');
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('model-status', { detail: data })
        );
      }
    });

    // === PHASE 56.5: CHAT-AS-TREE EVENT LISTENERS ===
    socket.on('chat_node_created', (data) => {
      // console.log('[Socket] Chat node created:', data.chatId, data.name);
      const { addChatNode } = useChatTreeStore.getState();
      addChatNode(data.parentId, {
        id: data.chatId,
        name: data.name,
        participants: data.participants,
        status: 'active',
      });
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('chat-node-created', { detail: data })
        );
      }
    });

    socket.on('chat_node_updated', (data) => {
      // console.log('[Socket] Chat node updated:', data.chatId);
      const { updateChatNode } = useChatTreeStore.getState();
      updateChatNode(data.chatId, {
        messageCount: data.messageCount,
        preview: data.preview,
      });
    });

    // MARKER_108_3_SOCKETIO_UPDATE: Phase 108.3 - Real-time chat node opacity updates
    socket.on('chat_node_update', (data: {
      chat_id: string;
      decay_factor: number;
      last_activity: string;
      message_count?: number;
    }) => {
      console.log('[Socket] Chat node update (opacity):', data.chat_id, 'decay:', data.decay_factor);

      // Update chatTreeStore with new decay_factor and activity
      const { updateChatNode } = useChatTreeStore.getState();
      updateChatNode(data.chat_id, {
        decay_factor: data.decay_factor,
        lastActivity: new Date(data.last_activity),
        messageCount: data.message_count,
      });

      // Update main store for 3D rendering
      // Chat nodes can be identified by chat_id or by group_id
      // Try both formats: direct chat_id and `chat_${chat_id}`
      const { nodes } = useStore.getState();
      const possibleIds = [data.chat_id, `chat_${data.chat_id}`];

      for (const nodeId of possibleIds) {
        if (nodes[nodeId]) {
          console.log('[Socket] Updating opacity for node:', nodeId, 'to', data.decay_factor);

          // Update opacity in main store for FileCard rendering with smooth transition
          useStore.setState((state) => ({
            nodes: {
              ...state.nodes,
              [nodeId]: {
                ...state.nodes[nodeId],
                opacity: data.decay_factor,
                // Also update metadata for consistency
                metadata: {
                  ...state.nodes[nodeId].metadata,
                  decay_factor: data.decay_factor,
                  message_count: data.message_count ?? state.nodes[nodeId].metadata?.message_count,
                  last_activity: data.last_activity,
                },
              },
            },
          }));
          break; // Found and updated, exit loop
        }
      }
    });

    socket.on('artifact_placeholder', (data) => {
      // console.log('[Socket] Artifact placeholder:', data.artifactId, data.name);
      const { addArtifactNode } = useChatTreeStore.getState();
      addArtifactNode(data.chatId, {
        id: data.artifactId,
        name: data.name,
        artifactType: data.artifactType as any,
        status: 'streaming',
        progress: 0,
      });
    });

    socket.on('artifact_stream', (data) => {
      // console.log('[Socket] Artifact streaming:', data.artifactId, data.progress + '%');
      const { updateArtifactNode } = useChatTreeStore.getState();
      updateArtifactNode(data.artifactId, {
        progress: data.progress,
      });
    });

    socket.on('artifact_complete', (data) => {
      // console.log('[Socket] Artifact complete:', data.artifactId);
      const { updateArtifactNode } = useChatTreeStore.getState();
      updateArtifactNode(data.artifactId, {
        status: 'done',
        progress: 100,
        preview: data.preview,
      });
    });

    socket.on('hostess_memory_tree', (data) => {
      // console.log('[Socket] Hostess memory updated:', data.nodes.length, 'nodes');
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('hostess-memory-tree', { detail: data })
        );
      }
    });

    // === PHASE 57.8: ARTIFACT TREE NODE ===
    socket.on('artifact_tree_node', (data: {
      id: string;
      name: string;
      type: 'artifact';
      artifact_type: string;
      parent_id: string;
      created_by: string;
      preview: string;
      language: string;
      size: number;
    }) => {
      // console.log('[Socket] Artifact tree node:', data.name, 'parent:', data.parent_id, 'by:', data.created_by);

      // Add as artifact node to chat tree
      const { addArtifactNode } = useChatTreeStore.getState();
      addArtifactNode(data.parent_id, {
        id: data.id,
        name: data.name,
        artifactType: data.artifact_type as any,
        status: 'done',
        progress: 100,
        preview: data.preview,
      });

      // Also dispatch to main tree via custom event
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('artifact-tree-node', { detail: data })
        );
      }
    });

    // === PHASE 57.9: API KEY LEARNING LISTENERS ===
    socket.on('key_saved', (data) => {
      // console.log('[Socket] Key saved:', data.provider, data.message);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('key-saved', { detail: data })
        );
      }
    });

    socket.on('key_learned', (data) => {
      // console.log('[Socket] Key learned:', data.provider);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('key-learned', { detail: data })
        );
      }
    });

    socket.on('unknown_key_type', (data) => {
      // console.log('[Socket] Unknown key type:', data.key_preview);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('unknown-key-type', { detail: data })
        );
      }
    });

    socket.on('key_status', (data) => {
      // console.log('[Socket] Key status:', data.active, '/', data.total, 'providers');
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('key-status', { detail: data })
        );
      }
    });

    socket.on('key_error', (data) => {
      console.error('[Socket] Key error:', data.error);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('key-error', { detail: data })
        );
      }
    });

    // === PHASE 68: SEARCH EVENT LISTENERS ===
    socket.on('search_results', (data) => {
      // console.log('[Socket] Search results:', data.total, 'in', data.took_ms, 'ms');
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('search-results', { detail: data })
        );
      }
    });

    socket.on('search_error', (data) => {
      console.error('[Socket] Search error:', data.error);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('search-error', { detail: data })
        );
      }
    });

    // === PHASE 69: MULTI-HIGHLIGHT FROM SEARCH ===
    socket.on('highlight_nodes', (data: { nodeIds: string[] }) => {
      const { highlightNodes, clearHighlights } = useStore.getState();
      highlightNodes(data.nodeIds);

      // Auto-clear after 5 seconds
      setTimeout(() => {
        clearHighlights();
      }, 5000);
    });

    // MARKER_104_FRONTEND
    // === PHASE 104.8: VOICE & ROOM EVENT HANDLERS ===

    socket.on('voice_transcript', (data: {
      text: string;
      is_final: boolean;
      confidence?: number;
      language?: string;
      timestamp?: string;
    }) => {
      console.log('[Socket] voice_transcript:', data.text.slice(0, 50), data.is_final ? '(final)' : '(partial)');
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('voice-transcript', { detail: data })
        );
      }
    });

    socket.on('jarvis_interrupt', (data: {
      priority: number;
      reason?: string;
      timestamp?: string;
    }) => {
      console.log('[Socket] jarvis_interrupt: priority', data.priority, data.reason || '');
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('jarvis-interrupt', { detail: data })
        );
      }
    });

    socket.on('jarvis_prediction', (data: {
      predictions: string[];
      context?: string;
      confidence?: number;
    }) => {
      console.log('[Socket] jarvis_prediction:', data.predictions.length, 'predictions');
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('jarvis-prediction', { detail: data })
        );
      }
    });

    socket.on('stream_error', (data: {
      error: string;
      stream_id?: string;
      code?: string;
    }) => {
      console.error('[Socket] stream_error:', data.error, data.code || '');
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('stream-error', { detail: data })
        );
      }
    });

    socket.on('room_joined', (data: {
      room_id: string;
      user_id?: string;
      participants?: string[];
    }) => {
      console.log('[Socket] room_joined:', data.room_id, data.participants?.length || 0, 'participants');
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('room-joined', { detail: data })
        );
      }
    });

    socket.on('room_left', (data: {
      room_id: string;
      user_id?: string;
      reason?: string;
    }) => {
      console.log('[Socket] room_left:', data.room_id, data.reason || '');
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('room-left', { detail: data })
        );
      }
    });

    // === PHASE 104.9: ARTIFACT APPROVAL EVENT HANDLER ===
    // MARKER_104_VISUAL - Dispatches artifact-approval CustomEvent for ArtifactPanel L2 editing
    socket.on('artifact_approval', (data: {
      artifactId: string;
      approvalLevel: 'L1' | 'L2' | 'L3';
      action?: 'approve' | 'reject' | 'edit';
      content?: string;
      reason?: string;
    }) => {
      console.log('[Socket] artifact_approval:', data.artifactId, data.approvalLevel, data.action || 'view');
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('artifact-approval', { detail: data })
        );
      }
    });

    return () => {
      // console.log('[Socket] Cleaning up...');
      // Phase 49.2: Cancel pending RAF and flush remaining tokens
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
        rafIdRef.current = null;
      }
      // Flush any remaining tokens before disconnecting
      if (tokenBufferRef.current.size > 0) {
        flushTokenBuffer();
      }
      socket.disconnect();
    };
  }, [
    setNodes,
    setNodesFromRecord,
    setEdges,
    updateNodePosition,
    setError,
    setSocketConnected,
    addMessage,
    setCameraCommand,
    highlightNode,
    addChatMessage,
    setWorkflowStatus,
    appendStreamingContent,
    setIsTyping,
    flushTokenBuffer,
    reloadTreeFromHttp,
  ]);

  const requestTree = useCallback(() => {
    socketRef.current?.emit('request_tree');
  }, []);

  const moveNode = useCallback((path: string, position: { x: number; y: number; z: number }) => {
    socketRef.current?.emit('move_node', { path, position });
  }, []);

  const selectNode = useCallback((path: string) => {
    socketRef.current?.emit('select_node', { path });
  }, []);

  // Phase 48.1: Added modelId parameter for model routing
  // Phase 61: Added pinned files for multi-file context
  // [PHASE70-M3] useSocket.ts: Viewport in sendMessage — IMPLEMENTED
  const sendMessage = useCallback((message: string, nodePath?: string, modelId?: string) => {
    if (!socketRef.current?.connected) {
      // console.warn('[Socket] Not connected, cannot send message');
      return;
    }

    // Phase 61: Get pinned files from store
    const pinnedFileIds = useStore.getState().pinnedFileIds;
    const nodesRecord = useStore.getState().nodes;

    // Build pinned files array with paths
    const pinnedFiles = pinnedFileIds
      .map(id => nodesRecord[id])
      .filter(Boolean)
      .map(node => ({
        id: node.id,
        path: node.path,
        name: node.name,
        type: node.type,
      }));

    // === PHASE 70: Viewport Context ===
    const camera = useStore.getState().cameraRef;
    let viewportContext: ViewportContext | null = null;

    if (camera) {
      viewportContext = buildViewportContext(nodesRecord, pinnedFileIds, camera);

      console.log(
        `[VIEWPORT] Context built: ` +
        `${viewportContext.total_pinned} pinned, ` +
        `${viewportContext.total_visible} visible, ` +
        `zoom ~${viewportContext.zoom_level}`
      );
    } else {
      console.log('[VIEWPORT] Camera not available, skipping viewport context');
    }

    // FIX_109.4: Get chat_id from store for unified MCP compatibility
    const currentChatId = useStore.getState().currentChatId;

    socketRef.current.emit('user_message', {
      text: message,                    // Backend expects 'text'
      node_path: nodePath || 'unknown', // Backend expects 'node_path'
      node_id: 'root',                  // Backend expects 'node_id'
      model: modelId,                   // Phase 48.1: Optional model override
      pinned_files: pinnedFiles.length > 0 ? pinnedFiles : undefined,  // Phase 61
      // Phase 70: Full viewport context for AI spatial awareness
      viewport_context: viewportContext || undefined,
      // FIX_109.4: Pass chat_id for unified ID system (solo chats like groups)
      chat_id: currentChatId || undefined,
    });
  }, []);

  // === PHASE 55: APPROVAL ACTIONS ===

  const approveArtifact = useCallback((requestId: string, reason?: string) => {
    if (!socketRef.current?.connected) {
      // console.warn('[Socket] Not connected, cannot approve');
      return;
    }

    socketRef.current.emit('approve_artifact', {
      request_id: requestId,
      reason: reason || 'Approved',
    });
    // console.log('[Socket] Emitted approve_artifact:', requestId);
  }, []);

  const rejectArtifact = useCallback((requestId: string, reason: string) => {
    if (!socketRef.current?.connected) {
      // console.warn('[Socket] Not connected, cannot reject');
      return;
    }

    socketRef.current.emit('reject_artifact', {
      request_id: requestId,
      reason,
    });
    // console.log('[Socket] Emitted reject_artifact:', requestId);
  }, []);

  // === PHASE 56: GROUP CHAT FUNCTIONS ===

  const joinGroup = useCallback((groupId: string) => {
    socketRef.current?.emit('join_group', { group_id: groupId });
    // console.log('[Socket] Emitted join_group:', groupId);
  }, []);

  const leaveGroup = useCallback((groupId: string) => {
    socketRef.current?.emit('leave_group', { group_id: groupId });
    // console.log('[Socket] Emitted leave_group:', groupId);
  }, []);

  // Phase 80.35: Added reply_to_id for reply routing
  const sendGroupMessage = useCallback((groupId: string, senderId: string, content: string, replyToId?: string) => {
    socketRef.current?.emit('group_message', {
      group_id: groupId,
      sender_id: senderId,
      content,
      reply_to_id: replyToId,  // Phase 80.35: Pass reply target for routing
    });
    // console.log('[Socket] Emitted group_message:', { groupId, senderId, replyToId });
  }, []);

  const sendTypingIndicator = useCallback((groupId: string, agentId: string) => {
    socketRef.current?.emit('group_typing', {
      group_id: groupId,
      agent_id: agentId,
    });
  }, []);

  // === PHASE 56.5: CHAT-AS-TREE FUNCTIONS ===

  const createChatNode = useCallback(
    (chatId: string, parentId: string, name: string, participants: string[]) => {
      if (!socketRef.current?.connected) {
        // console.warn('[Socket] Not connected, cannot create chat node');
        return;
      }

      // ✅ Use provided chatId from frontend store for sync
      socketRef.current.emit('create_chat_node', {
        chatId,
        parentId,
        name,
        participants,
      });
      // console.log('[Socket] Emitted create_chat_node:', chatId, name);
    },
    []
  );

  const getHostessMemory = useCallback(() => {
    if (!socketRef.current?.connected) {
      // console.warn('[Socket] Not connected, cannot get hostess memory');
      return;
    }

    socketRef.current.emit('get_hostess_memory', {});
    // console.log('[Socket] Emitted get_hostess_memory');
  }, []);

  // === PHASE 57.9: API KEY FUNCTIONS ===

  const addApiKey = useCallback((key: string) => {
    if (!socketRef.current?.connected) {
      // console.warn('[Socket] Not connected, cannot add API key');
      return;
    }

    socketRef.current.emit('add_api_key', { key });
    // console.log('[Socket] Emitted add_api_key');
  }, []);

  const learnKeyType = useCallback((key: string, provider: string) => {
    if (!socketRef.current?.connected) {
      // console.warn('[Socket] Not connected, cannot learn key type');
      return;
    }

    socketRef.current.emit('learn_key_type', { key, provider });
    // console.log('[Socket] Emitted learn_key_type:', provider);
  }, []);

  const getKeyStatus = useCallback((provider?: string) => {
    if (!socketRef.current?.connected) {
      // console.warn('[Socket] Not connected, cannot get key status');
      return;
    }

    socketRef.current.emit('get_key_status', provider ? { provider } : {});
    // console.log('[Socket] Emitted get_key_status:', provider || 'all');
  }, []);

  // === PHASE 68: SEARCH FUNCTIONS ===

  const searchQuery = useCallback((
    query: string,
    limit: number = 100,  // Phase 68.2: Increased default from 10 to 100
    mode: 'hybrid' | 'semantic' | 'keyword' | 'filename' = 'hybrid',
    filters: Record<string, unknown> = {},
    minScore: number = 0.3  // Phase 68.2: Minimum relevance threshold
  ) => {
    if (!socketRef.current?.connected) {
      console.warn('[Socket] Not connected, cannot search');
      return;
    }

    socketRef.current.emit('search_query', {
      text: query,
      limit,
      mode,
      filters,
      min_score: minScore  // Phase 68.2: Pass to backend for filtering
    });
    // console.log('[Socket] Emitted search_query:', query);
  }, []);

  return {
    isConnected: isSocketConnected,
    requestTree,
    moveNode,
    selectNode,
    sendMessage,
    // === PHASE 55: APPROVAL ACTIONS ===
    approveArtifact,
    rejectArtifact,
    // === PHASE 56: GROUP ACTIONS ===
    joinGroup,
    leaveGroup,
    sendGroupMessage,
    sendTypingIndicator,
    // === PHASE 56.5: CHAT-AS-TREE ACTIONS ===
    createChatNode,
    getHostessMemory,
    // === PHASE 57.9: API KEY ACTIONS ===
    addApiKey,
    learnKeyType,
    getKeyStatus,
    // === PHASE 68: SEARCH ACTIONS ===
    searchQuery,
  };
}
