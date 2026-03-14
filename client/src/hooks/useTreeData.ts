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
import { calculateSimpleLayout, setLayoutBiasProfile } from '../utils/layout';
import { fetchDagLayoutBiasProfile } from '../utils/dagLayoutPreferences';
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
import { API_BASE } from '../config/api.config';

const TREE_DEBUG = import.meta.env.VITE_TREE_DEBUG === '1';

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
    let cancelled = false;
    (async () => {
      try {
        const initRes = await fetch(`${API_BASE}/mcc/init`);
        let scopeRoot = 'default';
        if (initRes.ok) {
          const init = await initRes.json();
          const cfg = init?.project_config || {};
          scopeRoot = String(cfg.source_path || cfg.sandbox_path || 'default').replace(/\\/g, '/');
        }
        const graphType = treeViewMode === 'knowledge' ? 'architecture' : 'workflow';
        const scopeKey = `dag:${scopeRoot}:${graphType}`;
        const profile = await fetchDagLayoutBiasProfile(scopeKey);
        if (!cancelled) setLayoutBiasProfile(profile);
      } catch {
        if (!cancelled) setLayoutBiasProfile(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [treeViewMode, knowledgeScopePath]);

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
        if (TREE_DEBUG) {
          console.log(`[useTreeData] API returned ${response.tree.nodes?.length ?? 0} nodes`);
          console.log(`[useTreeData] After conversion: ${Object.keys(convertedNodes).length} nodes`);
        }

        // MARKER_108_CHAT_FRONTEND: Phase 108.2 - Process chat nodes
        let chatTreeNodes: TreeNode[] = [];
        let artifactTreeNodes: TreeNode[] = [];
        const chatEdges: typeof edges = [];
        const artifactEdges: typeof edges = [];

        if (response.chat_nodes && response.chat_nodes.length > 0) {
          if (TREE_DEBUG) {
            console.log('[useTreeData] Processing chat nodes:', response.chat_nodes.length);
          }

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

          if (TREE_DEBUG) {
            console.log('[useTreeData] Converted chat nodes:', chatTreeNodes.length);
            console.log('[useTreeData] Chat edges:', chatEdges.length);
          }
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
          if (TREE_DEBUG) {
            console.log('[useTreeData] Converted artifact nodes:', artifactTreeNodes.length);
            console.log('[useTreeData] Artifact edges:', artifactEdges.length);
          }
        }

        // Merge file tree nodes and chat nodes
        let allNodes = { ...convertedNodes };
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
        const knowledgeNodeIds = new Set<string>();
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
            let semanticExpansionBudget = 20; // folder default
            if (scopedPathSet.size <= 2) semanticExpansionBudget = 8; // file scope
            else if (scopedPathSet.size >= 400) semanticExpansionBudget = 80; // root-like scope

            const kg = await fetchKnowledgeGraphData({
              forceRefresh: false,
              hydrateScopePath: knowledgeScopePath || undefined,
              hydrateForce: false,
              filePositions: sceneFilePositions,
              semanticExpansionBudget,
              // MARKER_155.IMPL.A3_EXPANSION_THRESHOLD_DEFAULT:
              // 0.72 was too strict for many folders and produced degenerate tiny graphs.
              semanticExpansionThreshold: 0.62,
            });
            if (TREE_DEBUG) {
              console.log('[useTreeData] Knowledge mode response:', {
                status: kg.status,
                scope: knowledgeScopePath || 'global',
                sentFilePositions: Object.keys(sceneFilePositions).length,
                positions: kg.positions ? Object.keys(kg.positions).length : 0,
                edges: Array.isArray(kg.edges) ? kg.edges.length : 0,
                chainEdges: Array.isArray(kg.chain_edges) ? kg.chain_edges.length : 0,
              });
            }

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
              // Knowledge mode is a distinct visual language:
              // clear directed stems and rebuild semantic edges below.
              allEdges = [];

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
                knowledgeNodeIds.add(sceneNodeId!);

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

              // MARKER_155.KMODE.A3_BACKEND_COORDS:
              // Knowledge mode should use backend KG coordinates directly.
              // Frontend anchoring to Directed Y/Z was causing "sticks/cones".
              if (matchedNodes.length > 0) {
                matchedNodes.forEach((m) => {
                  const target = allNodes[m.nodeId];
                  if (!target) return;
                  target.position = {
                    x: m.kgX,
                    y: m.kgY,
                    z: m.kgZ,
                  };
                });
              }

              // MARKER_155.KMODE.TAG_LAYOUT_V1:
              // Build semantic tag hubs and redistribute scoped files around tags.
              const focusNode = Object.values(allNodes).find((node) => {
                const p = String((node as any)?.path || '').replace(/\\/g, '/').toLowerCase();
                return p === normalizedScope;
              });
              const focusX = Number(focusNode?.position?.x || 0);
              const focusY = Number(focusNode?.position?.y || 0);
              const focusZ = Number(focusNode?.position?.z || 0);

              const kgTags = (kg.tags && typeof kg.tags === 'object') ? kg.tags : {};
              const activeTagEntries = Object.entries(kgTags).filter(([, tagData]: any) => {
                const files = Array.isArray(tagData?.files) ? tagData.files : [];
                return files.some((rawFileId: string) => {
                  const sceneId = kgKeyToSceneNodeId.get(String(rawFileId))
                    || pathToSceneNodeId.get(String(rawFileId))
                    || (allNodes[String(rawFileId)] ? String(rawFileId) : '');
                  if (!sceneId) return false;
                  const scenePath = String((allNodes[sceneId] as any)?.path || '');
                  return Boolean(scenePath && scopedPathSet.has(scenePath));
                });
              });

              if (false && activeTagEntries.length > 0) {
                const tagRadius = Math.max(140, activeTagEntries.length * 42);
                const angleStep = (Math.PI * 2) / activeTagEntries.length;

                activeTagEntries.forEach(([tagId, tagData]: any, tagIndex) => {
                  const angle = tagIndex * angleStep;
                  const tagNodeId = `kg_tag_${tagId}`;
                  const tagX = focusX + Math.cos(angle) * tagRadius;
                  const tagY = focusY + Math.sin(angle) * (tagRadius * 0.5);
                  const tagZ = focusZ + 25;

                  allNodes[tagNodeId] = {
                    id: tagNodeId,
                    path: `kg://tag/${tagId}`,
                    name: String(tagData?.name || tagId || 'tag'),
                    type: 'folder',
                    backendType: 'branch',
                    depth: Number(focusNode?.depth || 0),
                    parentId: focusNode?.id || null,
                    position: { x: tagX, y: tagY, z: tagZ },
                    color: String(tagData?.color || '#7dd3fc'),
                    children: [],
                    metadata: {
                      context_type: 'knowledge_tag',
                      tag_id: tagId,
                    },
                  };

                  const rawFiles = Array.isArray(tagData?.files) ? tagData.files : [];
                  const scopedFileIds = rawFiles
                    .map((rawFileId: string) => kgKeyToSceneNodeId.get(String(rawFileId))
                      || pathToSceneNodeId.get(String(rawFileId))
                      || (allNodes[String(rawFileId)] ? String(rawFileId) : ''))
                    .filter((sceneId: string) => {
                      if (!sceneId) return false;
                      const scenePath = String((allNodes[sceneId] as any)?.path || '');
                      return Boolean(scenePath && scopedPathSet.has(scenePath));
                    });

                  const getTime = (nodeId: string): number => {
                    const n = allNodes[nodeId] as any;
                    const md = n?.metadata || {};
                    const c = Number(md.created_time || md.createdAt || 0);
                    const m = Number(md.modified_time || md.updated_at || md.mtime || 0);
                    if (Number.isFinite(c) && c > 0) return c;
                    if (Number.isFinite(m) && m > 0) return m;
                    return 0;
                  };
                  const getKl = (nodeId: string): number => {
                    const n = allNodes[nodeId] as any;
                    return Number(n?.metadata?.knowledge_level || 0);
                  };

                  const orderedScopedFiles = [...scopedFileIds].sort((a, b) => {
                    const ta = getTime(a);
                    const tb = getTime(b);
                    if (ta > 0 && tb > 0 && ta !== tb) return ta - tb; // older -> newer
                    const ka = getKl(a);
                    const kb = getKl(b);
                    if (Number.isFinite(ka) && Number.isFinite(kb) && ka !== kb) return ka - kb;
                    return a.localeCompare(b);
                  });

                  const fileCount = orderedScopedFiles.length;
                  const colStepY = 36;
                  const colStepX = 18;

                  orderedScopedFiles.forEach((fileNodeId: string, fileIdx: number) => {
                    const fileNode = allNodes[fileNodeId];
                    if (!fileNode) return;
                    if (fileCount <= 12) {
                      // MARKER_155.KMODE.NO_STICK_LAYOUT:
                      // Small sets should fan out horizontally around tag,
                      // not collapse into one vertical stem.
                      const center = (fileCount - 1) / 2;
                      const dx = (fileIdx - center) * 30;
                      fileNode.position = {
                        x: tagX + dx,
                        y: tagY + 82 + Math.abs(fileIdx - center) * 4,
                        z: focusZ + 8,
                      };
                    } else {
                      const col = Math.floor(fileIdx / 12);
                      const row = fileIdx % 12;
                      fileNode.position = {
                        x: tagX + col * colStepX,
                        y: tagY + 70 + row * colStepY,
                        z: focusZ + 8,
                      };
                    }
                  });

                  // MARKER_155.KMODE.TAG_ATTACH_ONLY:
                  // Keep tag attachment edge only; semantic DAG comes from backend edges.
                  // Avoid synthetic long chain that turns graph into a vertical "stick".
                  if (orderedScopedFiles.length > 0) {
                    allEdges.push({
                      id: `kg_tag_edge_${tagNodeId}_${orderedScopedFiles[0]}`,
                      source: tagNodeId,
                      target: orderedScopedFiles[0],
                      type: 'knowledge_tag',
                    });
                  }
                });
              }
            } else if (kg.status === 'error') {
              console.warn('[useTreeData] Knowledge mode fetch failed:', kg.error);
            }

            const kgEdges = Array.isArray(kg.edges) ? kg.edges : [];
            const extraEdges = [...kgEdges];
            const skipSemanticOverlay = false;
            const SEMANTIC_TOP_K_OUT = 2;

            const knownEdgeIds = new Set(allEdges.map((e) => `${e.source}|${e.target}|${e.type}`));
            const adjacency = new Map<string, Set<string>>();
            const addAdj = (from: string, to: string) => {
              if (!adjacency.has(from)) adjacency.set(from, new Set());
              adjacency.get(from)!.add(to);
            };
            const wouldCreateCycle = (from: string, to: string): boolean => {
              if (from === to) return true;
              const stack = [to];
              const visited = new Set<string>();
              while (stack.length > 0) {
                const cur = stack.pop()!;
                if (cur === from) return true;
                if (visited.has(cur)) continue;
                visited.add(cur);
                const next = adjacency.get(cur);
                if (!next) continue;
                next.forEach((n) => {
                  if (!visited.has(n)) stack.push(n);
                });
              }
              return false;
            };

            // Seed adjacency with current (already accepted) edges.
            allEdges.forEach((edge) => {
              if (!edge?.source || !edge?.target) return;
              addAdj(edge.source, edge.target);
            });

            const getNodeTime = (nodeId: string): number => {
              const node = allNodes[nodeId] as any;
              if (!node) return 0;
              const md = node.metadata || {};
              const created = Number(md.created_time || md.createdAt || 0);
              const modified = Number(md.modified_time || md.updated_at || md.mtime || 0);
              if (Number.isFinite(created) && created > 0) return created;
              if (Number.isFinite(modified) && modified > 0) return modified;
              return 0;
            };

            const semanticCandidates: Array<{ from: string; to: string; weight: number; idx: number }> = [];
              extraEdges.forEach((edge: any, idx) => {
              if (skipSemanticOverlay) return;
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
              // MARKER_155.KMODE.DAG_ENFORCE:
              // Enforce acyclic semantic graph:
              // 1) orient by time (older -> newer), 2) deterministic tie-break, 3) cycle guard.
              let from = source;
              let to = target;
              const tFrom = getNodeTime(from);
              const tTo = getNodeTime(to);
              if (tFrom > 0 && tTo > 0 && tFrom !== tTo) {
                if (tFrom > tTo) {
                  from = target;
                  to = source;
                }
              } else if (from > to) {
                // deterministic fallback when timestamps absent/equal
                from = target;
                to = source;
              }

              if (from === to) return;
              const w = Number((edge as any).weight ?? (edge as any).score ?? 0.5);
              semanticCandidates.push({
                from,
                to,
                weight: Number.isFinite(w) ? w : 0.5,
                idx,
              });
            });

            // MARKER_155.KMODE.TOPK_THINNING:
            // Keep only strongest semantic edges per source, then enforce DAG.
            const outCount = new Map<string, number>();
            semanticCandidates
              .sort((a, b) => b.weight - a.weight)
              .forEach((cand) => {
                const usedOut = outCount.get(cand.from) || 0;
                if (usedOut >= SEMANTIC_TOP_K_OUT) return;
                const dedupKey = `${cand.from}|${cand.to}|semantic`;
                if (knownEdgeIds.has(dedupKey)) return;
                if (wouldCreateCycle(cand.from, cand.to)) return;
                knownEdgeIds.add(dedupKey);
                outCount.set(cand.from, usedOut + 1);
                addAdj(cand.from, cand.to);
                knowledgeNodeIds.add(cand.from);
                knowledgeNodeIds.add(cand.to);
                allEdges.push({
                  id: `kg_${cand.from}_${cand.to}_${cand.idx}`,
                  source: cand.from,
                  target: cand.to,
                  type: 'knowledge_semantic',
                });
              });

            // MARKER_155.KMODE.TOPOLOGICAL_LAYERING:
            // Frontend layering disabled in A.3; backend now owns DAG layering.
            if (false && treeViewMode === 'knowledge' && scopedPathSet.size > 0) {
              const scopedNodeIds = new Set<string>(
                Object.entries(allNodes)
                  .filter(([, n]) => {
                    const p = String((n as any)?.path || '');
                    return Boolean(p && scopedPathSet.has(p));
                  })
                  .map(([id]) => id)
              );

              // Include knowledge tag hubs in layout layers.
              Object.keys(allNodes).forEach((id) => {
                if (id.startsWith('kg_tag_')) scopedNodeIds.add(id);
              });

              const dagEdges = allEdges.filter((e) => scopedNodeIds.has(e.source) && scopedNodeIds.has(e.target));
              const indeg = new Map<string, number>();
              const outs = new Map<string, string[]>();
              scopedNodeIds.forEach((id) => {
                indeg.set(id, 0);
                outs.set(id, []);
              });
              dagEdges.forEach((e) => {
                indeg.set(e.target, (indeg.get(e.target) || 0) + 1);
                outs.get(e.source)?.push(e.target);
              });

              const queue: string[] = Array.from(scopedNodeIds).filter((id) => (indeg.get(id) || 0) === 0);
              const layer = new Map<string, number>();
              queue.forEach((id) => layer.set(id, 0));

              while (queue.length > 0) {
                const cur = queue.shift()!;
                const curLayer = layer.get(cur) || 0;
                (outs.get(cur) || []).forEach((nxt) => {
                  layer.set(nxt, Math.max(layer.get(nxt) || 0, curLayer + 1));
                  indeg.set(nxt, (indeg.get(nxt) || 0) - 1);
                  if ((indeg.get(nxt) || 0) === 0) queue.push(nxt);
                });
              }

              // Fallback for any residual nodes.
              scopedNodeIds.forEach((id) => {
                if (!layer.has(id)) layer.set(id, 0);
              });

              const layers = new Map<number, string[]>();
              layer.forEach((lv, id) => {
                if (!layers.has(lv)) layers.set(lv, []);
                layers.get(lv)!.push(id);
              });

              const focusNode = Object.values(allNodes).find((node) => {
                const p = String((node as any)?.path || '').replace(/\\/g, '/').toLowerCase();
                return p === normalizedScope;
              });
              const baseX = Number(focusNode?.position?.x || 0);
              const baseY = Number(focusNode?.position?.y || 0);
              const baseZ = Number(focusNode?.position?.z || 0);
              const LAYER_GAP_Y = 68;
              const NODE_GAP_X = 42;

              const layerSizes = Array.from(layers.values()).map((ids) => ids.length);
              const avgLayerSize = layerSizes.length
                ? layerSizes.reduce((a, b) => a + b, 0) / layerSizes.length
                : 0;
              const shouldApplyLayering = avgLayerSize >= 1.6;

              if (shouldApplyLayering) {
                Array.from(layers.entries())
                  .sort((a, b) => a[0] - b[0])
                  .forEach(([lv, ids]) => {
                    const sortedIds = [...ids].sort((a, b) => {
                      const na = allNodes[a];
                      const nb = allNodes[b];
                      const an = String(na?.name || a);
                      const bn = String(nb?.name || b);
                      return an.localeCompare(bn);
                    });
                    const centerOffset = (sortedIds.length - 1) / 2;
                    sortedIds.forEach((id, idx) => {
                      const node = allNodes[id];
                      if (!node) return;
                      node.position = {
                        x: baseX + (idx - centerOffset) * NODE_GAP_X,
                        y: baseY + 90 + lv * LAYER_GAP_Y,
                        z: baseZ + (id.startsWith('kg_tag_') ? 22 : 8),
                      };
                    });
                  });
              }
            }
          } catch (kgErr) {
            console.error('[useTreeData] Knowledge overlay failed, keeping directed layout:', kgErr);
          }
        }

        // MARKER_155.KMODE.LENS_V1:
        // Knowledge mode should act as a focused lens for selected folder scope.
        // Keep only nodes participating in computed KG (scope + semantic expansion).
        if (treeViewMode === 'knowledge' && knowledgeScopePath) {
          const focusNode = Object.values(allNodes).find((node) => {
            const p = String((node as any)?.path || '').replace(/\\/g, '/').toLowerCase();
            return p === String(knowledgeScopePath).replace(/\\/g, '/').toLowerCase();
          });
          if (focusNode?.id) {
            knowledgeNodeIds.add(focusNode.id);
          }

          if (knowledgeNodeIds.size > 0) {
            const scopedNodes: Record<string, TreeNode> = {};
            knowledgeNodeIds.forEach((id) => {
              if (allNodes[id]) scopedNodes[id] = allNodes[id];
            });
            allNodes = scopedNodes;
            allEdges = allEdges.filter((edge) => Boolean(allNodes[edge.source] && allNodes[edge.target]));
            Object.values(allNodes).forEach((node) => {
              if (!Array.isArray(node.children)) return;
              node.children = node.children.filter((childId) => Boolean(allNodes[childId]));
            });
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
      const nextMode: TreeViewMode = requestedMode === 'knowledge'
        ? 'knowledge'
        : requestedMode === 'media_edit'
          ? 'media_edit'
          : 'directed';
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
