/**
 * Hook for loading and managing tree data from VETKA API.
 * Handles both new VETKA format and legacy API responses with automatic layout.
 *
 * @status active
 * @phase 96
 * @depends zustand, apiConverter, layout
 * @used_by App, TreeViewer
 */

import { useEffect, useState } from 'react';
import { useStore, TreeNode, VetkaNodeType } from '../store/useStore';
import { fetchTreeData, ApiTreeNode } from '../utils/api';
import { calculateSimpleLayout } from '../utils/layout';
import {
  convertApiResponse,
  convertLegacyNode,
  convertLegacyEdge,
  convertChatNode,
  convertChatEdge,
  chatNodeToTreeNode,
  VetkaApiResponse,
} from '../utils/apiConverter';
import { getDevPanelConfig } from '../utils/devConfig';
import { useChatTreeStore } from '../store/chatTreeStore';

export function useTreeData() {
  const {
    setNodes,
    setNodesFromRecord,
    setEdges,
    setLoading,
    setError,
    nodes,
    isLoading,
    error,
  } = useStore();

  // MARKER_108_CHAT_FRONTEND: Phase 108.2 - Chat tree store for chat nodes
  const { addChatNode } = useChatTreeStore();

  // MARKER_110_FIX: Trigger for manual tree refresh (from DevPanel)
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);

      const response = await fetchTreeData();

      if (!response.success) {
        setError(response.error || 'Failed to load tree data');
        setLoading(false);

        // console.warn('[useTreeData] API unavailable, using demo data');
        const demoNodes = getDemoNodes();
        const positioned = calculateSimpleLayout(demoNodes);
        setNodes(positioned);
        return;
      }

      // Check if response is new VETKA format or legacy format
      if (response.tree) {
        // New VETKA API format
        const vetkaResponse: VetkaApiResponse = {
          tree: {
            nodes: response.tree.nodes,
            edges: response.tree.edges || [],
          },
        };

        const { nodes: convertedNodes, edges } = convertApiResponse(vetkaResponse);

        // MARKER_111_DEBUG: Log node count at each step
        console.log(`[useTreeData] API returned ${response.tree.nodes?.length ?? 0} nodes`);
        console.log(`[useTreeData] After conversion: ${Object.keys(convertedNodes).length} nodes`);

        // MARKER_108_CHAT_FRONTEND: Phase 108.2 - Process chat nodes
        let chatTreeNodes: TreeNode[] = [];
        const chatEdges: typeof edges = [];

        if (response.chat_nodes && response.chat_nodes.length > 0) {
          console.log('[useTreeData] Processing chat nodes:', response.chat_nodes.length);

          // Convert chat nodes to ChatNode type and add to chatTreeStore
          response.chat_nodes.forEach((apiChatNode) => {
            const chatNode = convertChatNode(apiChatNode);
            addChatNode(chatNode.parentId, chatNode);

            // Convert ChatNode to TreeNode for 3D rendering
            const position = {
              x: apiChatNode.visual_hints.layout_hint.expected_x,
              y: apiChatNode.visual_hints.layout_hint.expected_y,
              z: apiChatNode.visual_hints.layout_hint.expected_z,
            };
            const treeNode = chatNodeToTreeNode(chatNode, position);
            chatTreeNodes.push(treeNode);
          });

          // Convert chat edges
          if (response.chat_edges) {
            response.chat_edges.forEach((apiChatEdge, idx) => {
              chatEdges.push(convertChatEdge(apiChatEdge, idx));
            });
          }

          console.log('[useTreeData] Converted chat nodes:', chatTreeNodes.length);
          console.log('[useTreeData] Chat edges:', chatEdges.length);
        }

        // Merge file tree nodes and chat nodes
        const allNodes = { ...convertedNodes };
        chatTreeNodes.forEach((chatNode) => {
          allNodes[chatNode.id] = chatNode;
        });

        // Merge edges
        const allEdges = [...edges, ...chatEdges];

        // MARKER_109_DEVPANEL: Threshold-based fallback for layout
        const config = getDevPanelConfig();
        const nodeArray = Object.values(allNodes);
        const totalNodes = nodeArray.length;

        // MARKER_111_FIX: Count nodes with TRULY invalid positions
        // Y=0 is VALID for root nodes! Only count as invalid if ALL coords are exactly 0
        // AND it's not a root node (depth > 0 or has parent)
        const invalidCount = nodeArray.filter(
          (n) => {
            const isZeroPosition = n.position.x === 0 && n.position.y === 0 && n.position.z === 0;
            const isRootNode = n.depth === 0 || !n.parentId;
            // Root nodes with (0,0,0) are VALID - they should be at origin
            // Only non-root nodes with (0,0,0) are invalid
            return isZeroPosition && !isRootNode;
          }
        ).length;

        const invalidRatio = totalNodes > 0 ? invalidCount / totalNodes : 0;
        const needsLayout = invalidRatio > (config.FALLBACK_THRESHOLD ?? 0.5);

        // MARKER_109_DEVPANEL: If semantic fallback enabled, try semantic_position first
        if (config.USE_SEMANTIC_FALLBACK && !needsLayout) {
          nodeArray.forEach((node) => {
            if (node.position.x === 0 && node.position.y === 0 && node.position.z === 0) {
              // Check for semanticPosition on the node
              const semanticPos = (node as any).semanticPosition;
              if (semanticPos) {
                node.position = {
                  x: semanticPos.x,
                  y: semanticPos.y,
                  z: semanticPos.z,
                };
              }
            }
          });
        }

        // MARKER_111_FIX: Backend уже сделал layout в fan_layout.py
        // НЕ перезаписываем позиции! Fallback ломал всё дерево
        if (needsLayout) {
          console.warn(`[useTreeData] Layout fallback DISABLED (Phase 111): ${invalidCount}/${totalNodes} nodes would trigger, but backend positions preserved`);
        }

        // MARKER_111_DEBUG: Final count before store
        console.log(`[useTreeData] Setting ${Object.keys(allNodes).length} nodes to store`);
        setNodesFromRecord(allNodes);

        // Phase 113.1: Restore saved positions — DISABLED (Phase 113.3 cleanup)
        // Positions come from backend fan_layout.py, no localStorage override needed
        // useStore.getState().loadPositions();

        setEdges(allEdges);
      } else if (response.nodes) {
        // Legacy API format
        const treeNodes: TreeNode[] = response.nodes.map((n: ApiTreeNode) =>
          convertLegacyNode({
            path: n.path,
            name: n.name,
            type: n.type,
            depth: n.depth,
            parent_path: n.parent_path,
            position: n.position,
            children: n.children,
          })
        );

        const positioned = calculateSimpleLayout(treeNodes);
        setNodes(positioned);

        if (response.edges) {
          setEdges(
            response.edges.map((e: { source: string; target: string }, i: number) =>
              convertLegacyEdge(e, i)
            )
          );
        }
      }

      setLoading(false);
    }

    loadData();
  }, [setNodes, setNodesFromRecord, setEdges, setLoading, setError, addChatNode, refreshTrigger]);

  // MARKER_110_FIX: Listen for tree refresh events from DevPanel
  useEffect(() => {
    const handleTreeRefresh = () => {
      console.log('[useTreeData] Received vetka-tree-refresh-needed event, triggering refetch...');
      // Increment trigger to cause useEffect re-run
      setRefreshTrigger(prev => prev + 1);
    };

    window.addEventListener('vetka-tree-refresh-needed', handleTreeRefresh);
    return () => {
      window.removeEventListener('vetka-tree-refresh-needed', handleTreeRefresh);
    };
  }, []);

  return { nodes, isLoading, error };
}

function getDemoNodes(): TreeNode[] {
  const makeNode = (
    id: string,
    name: string,
    type: 'file' | 'folder',
    depth: number,
    parentId: string | null,
    color: string
  ): TreeNode => {
    const backendType: VetkaNodeType =
      depth === 0 ? 'root' : type === 'folder' ? 'branch' : 'leaf';

    return {
      id,
      path: id,
      name,
      type,
      backendType,
      depth,
      parentId,
      position: { x: 0, y: 0, z: 0 },
      color,
    };
  };

  return [
    makeNode('/root', 'vetka_project', 'folder', 0, null, '#6366f1'),
    makeNode('/root/src', 'src', 'folder', 1, '/root', '#374151'),
    makeNode('/root/client', 'client', 'folder', 1, '/root', '#374151'),
    makeNode('/root/src/main.py', 'main.py', 'file', 2, '/root/src', '#1f2937'),
    makeNode('/root/src/config.py', 'config.py', 'file', 2, '/root/src', '#1f2937'),
    makeNode('/root/client/App.tsx', 'App.tsx', 'file', 2, '/root/client', '#1f2937'),
    makeNode('/root/README.md', 'README.md', 'file', 1, '/root', '#1f2937'),
  ];
}
