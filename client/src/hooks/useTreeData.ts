/**
 * Hook for loading and managing tree data from VETKA API.
 * Handles both new VETKA format and legacy API responses with automatic layout.
 *
 * @status active
 * @phase 96
 * @depends zustand, apiConverter, layout
 * @used_by App, TreeViewer
 */

import { useEffect } from 'react';
import { useStore, TreeNode, VetkaNodeType } from '../store/useStore';
import { fetchTreeData, ApiTreeNode } from '../utils/api';
import { calculateSimpleLayout } from '../utils/layout';
import {
  convertApiResponse,
  convertLegacyNode,
  convertLegacyEdge,
  VetkaApiResponse,
} from '../utils/apiConverter';

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

        // Apply layout if positions are all zeros
        const needsLayout = Object.values(convertedNodes).every(
          (n) => n.position.x === 0 && n.position.y === 0 && n.position.z === 0
        );

        if (needsLayout) {
          const positioned = calculateSimpleLayout(Object.values(convertedNodes));
          setNodes(positioned);
        } else {
          setNodesFromRecord(convertedNodes);
        }

        setEdges(edges);
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
  }, [setNodes, setNodesFromRecord, setEdges, setLoading, setError]);

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
