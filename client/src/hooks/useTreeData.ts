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
import { useStore, TreeNode } from '../store/useStore';
import {
  fetchTreeData,
  ApiTreeNode,
  fetchKnowledgeGraphData,
  TreeViewMode,
} from '../utils/api';
import { calculateSimpleLayout } from '../utils/layout';
import {
  convertApiResponse,
  convertLegacyNode,
  convertLegacyEdge,
  convertChatNode,
  convertChatEdge,
  chatNodeToTreeNode,
  convertArtifactNode,
  convertArtifactEdge,
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
  const [treeViewMode, setTreeViewMode] = useState<TreeViewMode>('directed');
  const [knowledgeScopePath, setKnowledgeScopePath] = useState<string>('');
  // MARKER_136.TREE_REFRESH_DEDUP_TREEHOOK: collapse bursty refresh events
  const [lastRefreshEventTs, setLastRefreshEventTs] = useState(0);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);

      const response = await fetchTreeData();

      if (!response.success) {
        setError(response.error || 'Failed to load tree data');
        setLoading(false);
        // MARKER_155.KMODE.FAILSAFE:
        // Never replace real graph with demo nodes on transient API failure.
        // Keep current store state to avoid collapsing scene to 7-node demo graph.
        console.warn('[useTreeData] fetchTreeData failed; preserving current graph state');
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
        let artifactTreeNodes: TreeNode[] = [];
        const chatEdges: typeof edges = [];
        const artifactEdges: typeof edges = [];

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

        // MARKER_153.IMPL.G09_ARTIFACT_TREE_FRONTEND:
        // Merge artifact/media-chunk nodes and edges from backend tree API.
        if (response.artifact_nodes && response.artifact_nodes.length > 0) {
          artifactTreeNodes = response.artifact_nodes.map((apiArtifactNode) => convertArtifactNode(apiArtifactNode));
          if (response.artifact_edges) {
            response.artifact_edges.forEach((apiArtifactEdge, idx) => {
              artifactEdges.push(convertArtifactEdge(apiArtifactEdge, idx));
            });
          }
          console.log('[useTreeData] Converted artifact nodes:', artifactTreeNodes.length);
          console.log('[useTreeData] Artifact edges:', artifactEdges.length);
        }

        // Merge file tree nodes and chat nodes
        const allNodes = { ...convertedNodes };
        chatTreeNodes.forEach((chatNode) => {
          allNodes[chatNode.id] = chatNode;
        });
        artifactTreeNodes.forEach((artifactNode) => {
          allNodes[artifactNode.id] = artifactNode;
        });

        // Merge edges
        let allEdges = [...edges, ...chatEdges, ...artifactEdges];

        // Ensure children arrays are complete for imported chat/artifact edges.
        allEdges.forEach((edge) => {
          const parentNode = allNodes[edge.source];
          if (!parentNode) return;
          if (!parentNode.children) parentNode.children = [];
          if (!parentNode.children.includes(edge.target)) {
            parentNode.children.push(edge.target);
          }
        });

        // Knowledge mode overlay: use KG positions/extra edges on top of tree payload.
        if (treeViewMode === 'knowledge') {
          try {
            // MARKER_155.KMODE.FILE_POSITIONS:
            // Backend Knowledge builder expects scene file paths in `file_positions`
            // for stable ID mapping (path -> qdrant_id) and scope filtering.
            const sceneFilePositions: Record<string, { x: number; y: number; z: number }> = {};
            const normalizedScope = String(knowledgeScopePath || '').replace(/\\/g, '/').toLowerCase();
            Object.values(allNodes).forEach((node) => {
              if (!node?.path) return;
              if (node.type !== 'file') return;
              const normalizedPath = String(node.path).replace(/\\/g, '/').toLowerCase();
              if (normalizedScope && !normalizedPath.startsWith(normalizedScope)) return;
              sceneFilePositions[node.path] = {
                x: Number(node.position?.x || 0),
                y: Number(node.position?.y || 0),
                z: Number(node.position?.z || 0),
              };
            });
            const scopedPathSet = new Set(Object.keys(sceneFilePositions));

            const kg = await fetchKnowledgeGraphData({
              forceRefresh: false,
              hydrateScopePath: knowledgeScopePath || undefined,
              hydrateForce: false,
              filePositions: sceneFilePositions,
            });
            console.log('[useTreeData] Knowledge mode response:', {
              status: kg.status,
              scope: knowledgeScopePath || 'global',
              sentFilePositions: Object.keys(sceneFilePositions).length,
              positions: kg.positions ? Object.keys(kg.positions).length : 0,
              edges: Array.isArray(kg.edges) ? kg.edges.length : 0,
              chainEdges: Array.isArray(kg.chain_edges) ? kg.chain_edges.length : 0,
            });

            // Resolver: frontend scene uses TreeNode IDs, KG may return qdrant IDs or paths.
            const pathToSceneNodeId = new Map<string, string>();
            Object.values(allNodes).forEach((node) => {
              if (node?.path) pathToSceneNodeId.set(node.path, node.id);
            });

            const kgKeyToSceneNodeId = new Map<string, string>();
            const resolveSceneNodeId = (rawKey: unknown, posObj?: any): string | null => {
              const key = String(rawKey || '');
              const posPath = String(posObj?.path || posObj?.file_path || '');
              if (key && allNodes[key]) return key;
              if (key && pathToSceneNodeId.has(key)) return pathToSceneNodeId.get(key) || null;
              if (posPath && pathToSceneNodeId.has(posPath)) return pathToSceneNodeId.get(posPath) || null;
              return null;
            };

            if (kg.status === 'ok' && kg.positions && typeof kg.positions === 'object') {
              const matchedNodes: Array<{
                nodeId: string;
                kgX: number;
                kgY: number;
                kgZ: number;
                oldX: number;
              }> = [];

              Object.entries(kg.positions).forEach(([kgNodeKey, pos]) => {
                const sceneNodeId = resolveSceneNodeId(kgNodeKey, pos);
                if (sceneNodeId) kgKeyToSceneNodeId.set(String(kgNodeKey), sceneNodeId);
                const target = sceneNodeId ? allNodes[sceneNodeId] : undefined;
                if (!target || !pos || typeof pos !== 'object') return;
                const targetPath = String((target as any)?.path || '');
                if (scopedPathSet.size > 0 && targetPath && !scopedPathSet.has(targetPath)) return;

                const kgX = Number((pos as any).x);
                const kgY = Number((pos as any).y);
                const kgZ = Number((pos as any).z);

                if (!Number.isFinite(kgX)) return;
                matchedNodes.push({
                  nodeId: sceneNodeId!,
                  kgX,
                  kgY: Number.isFinite(kgY) ? kgY : 0,
                  kgZ: Number.isFinite(kgZ) ? kgZ : 0,
                  oldX: Number(target.position.x || 0),
                });

                const kl = Number((pos as any).knowledge_level);
                if (Number.isFinite(kl)) {
                  target.metadata = {
                    ...(target.metadata || {}),
                    knowledge_level: kl,
                  };
                }
              });

              // MARKER_155.KMODE.ANCHORED_COORDS:
              // Keep Directed Y/Z stability (no "fall to ground").
              // Apply only anchored X-shift from KG so branch keeps its level/height.
              if (matchedNodes.length > 0) {
                const xOffsets = matchedNodes.map((m) => m.oldX - m.kgX).sort((a, b) => a - b);
                const medianOffsetX = xOffsets[Math.floor(xOffsets.length / 2)] || 0;
                matchedNodes.forEach((m) => {
                  const target = allNodes[m.nodeId];
                  if (!target) return;
                  target.position = {
                    x: m.kgX + medianOffsetX,
                    y: target.position.y, // preserve current Directed height
                    z: target.position.z, // preserve current Z layer
                  };
                });
              }
            } else if (kg.status === 'error') {
              console.warn('[useTreeData] Knowledge mode fetch failed:', kg.error);
            }

            const kgEdges = Array.isArray(kg.edges) ? kg.edges : [];
            const kgChainEdges = Array.isArray(kg.chain_edges) ? kg.chain_edges : [];
            const extraEdges = [...kgEdges, ...kgChainEdges];

            const knownEdgeIds = new Set(allEdges.map((e) => `${e.source}|${e.target}|${e.type}`));
            extraEdges.forEach((edge: any, idx) => {
              if (!edge || typeof edge !== 'object') return;
              const rawSource = String(edge.source || edge.from || '');
              const rawTarget = String(edge.target || edge.to || '');
              if (!rawSource || !rawTarget) return;

              const source = kgKeyToSceneNodeId.get(rawSource)
                || pathToSceneNodeId.get(rawSource)
                || (allNodes[rawSource] ? rawSource : '');
              const target = kgKeyToSceneNodeId.get(rawTarget)
                || pathToSceneNodeId.get(rawTarget)
                || (allNodes[rawTarget] ? rawTarget : '');

              if (!source || !target) return;
              if (!allNodes[source] || !allNodes[target]) return;
              const sourcePath = String((allNodes[source] as any)?.path || '');
              const targetPath = String((allNodes[target] as any)?.path || '');
              if (scopedPathSet.size > 0) {
                if (!sourcePath || !targetPath) return;
                if (!scopedPathSet.has(sourcePath) || !scopedPathSet.has(targetPath)) return;
              }
              const dedupKey = `${source}|${target}|semantic`;
              if (knownEdgeIds.has(dedupKey)) return;
              knownEdgeIds.add(dedupKey);
              allEdges.push({
                id: `kg_${source}_${target}_${idx}`,
                source,
                target,
                type: 'contains',
              });
            });
          } catch (kgErr) {
            console.error('[useTreeData] Knowledge overlay failed, keeping directed layout:', kgErr);
          }
        }

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
        window.dispatchEvent(
          new CustomEvent('vetka-tree-mode-changed', {
            detail: {
              mode: treeViewMode,
              scopePath: knowledgeScopePath || '',
            },
          })
        );

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
  }, [setNodes, setNodesFromRecord, setEdges, setLoading, setError, addChatNode, refreshTrigger, treeViewMode, knowledgeScopePath]);

  // MARKER_110_FIX: Listen for tree refresh events from DevPanel
  useEffect(() => {
    const handleTreeRefresh = () => {
      const now = Date.now();
      // Ignore duplicated refresh events fired in quick succession.
      if (now - lastRefreshEventTs < 350) return;
      setLastRefreshEventTs(now);
      console.log('[useTreeData] Received vetka-tree-refresh-needed event, triggering refetch...');
      // Increment trigger to cause useEffect re-run
      setRefreshTrigger(prev => prev + 1);
    };

    window.addEventListener('vetka-tree-refresh-needed', handleTreeRefresh);
    return () => {
      window.removeEventListener('vetka-tree-refresh-needed', handleTreeRefresh);
    };
  }, [lastRefreshEventTs]);

  useEffect(() => {
    const handleSwitchMode = (evt: Event) => {
      const e = evt as CustomEvent;
      const requestedMode = String(e.detail?.mode || '').toLowerCase();
      const nextMode: TreeViewMode = requestedMode === 'knowledge' ? 'knowledge' : 'directed';
      const scopePath = String(e.detail?.scopePath || '');
      setTreeViewMode(nextMode);
      setKnowledgeScopePath(scopePath);
      setRefreshTrigger(prev => prev + 1);
    };

    window.addEventListener('vetka-switch-tree-mode', handleSwitchMode);
    return () => {
      window.removeEventListener('vetka-switch-tree-mode', handleSwitchMode);
    };
  }, []);

  return { nodes, isLoading, error };
}
