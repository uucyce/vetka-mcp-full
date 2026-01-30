"""
VETKA Sugiyama Position Calculator.
Version: 1.0 | Date: December 18, 2025

Implements Sugiyama-style layered layout algorithm for VETKA tree visualization.
Phases:
1. Layer Assignment - assign nodes to layers by depth
2. Crossing Reduction - minimize edge crossings using barycenter method
3. Coordinate Assignment - calculate X, Y, Z positions
4. Repulsion Forces - apply forces for organic look

@status: active
@phase: 96
@depends: typing, dataclasses, collections, math
@used_by: src.visualizer.tree_renderer, src.api.routes.tree_routes
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from collections import defaultdict
import math


@dataclass
class NodePosition:
    """Position data for a node in 3D space."""
    x: float
    y: float
    z: float
    layer: int
    index: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            'x': self.x,
            'y': self.y,
            'z': self.z,
            'layer': self.layer,
            'index': self.index
        }


class VETKASugiyamaLayout:
    """
    Sugiyama-style layered layout for VETKA.

    Creates hierarchical tree layout with:
    - Layers based on folder depth
    - Minimized edge crossings
    - Balanced node distribution
    - Organic feel via repulsion forces
    """

    def __init__(self, layer_height: float = 80.0, node_spacing: float = 120.0, base_y: float = 50.0):
        """
        Initialize layout calculator.

        Args:
            layer_height: Vertical distance between layers
            node_spacing: Horizontal distance between nodes in same layer
            base_y: Starting Y position for root layer
        """
        self.LAYER_HEIGHT = layer_height
        self.NODE_SPACING = node_spacing
        self.BASE_Y = base_y

    def calculate(self, nodes: List[Dict], edges: List[Dict]) -> Dict[str, NodePosition]:
        """
        Calculate positions for all nodes.

        Args:
            nodes: List of node dictionaries with 'id', 'name', 'metadata'
            edges: List of edge dictionaries with 'source', 'target'

        Returns:
            Dictionary mapping node IDs to NodePosition objects
        """
        print(f'[Sugiyama] Calculating layout for {len(nodes)} nodes')

        if not nodes:
            return {}

        # Phase 1: Layer Assignment (using longest path method)
        layers = self._assign_layers(nodes, edges)
        print(f'[Sugiyama] Created {len(layers)} layers')

        # Phase 2: Crossing Reduction
        ordered_layers = self._minimize_crossings(layers, edges)

        # Phase 3: Coordinate Assignment
        positions = self._calculate_coordinates(ordered_layers)

        # Phase 4: Repulsion Forces
        self._apply_repulsion(positions)

        print('[Sugiyama] Layout complete')
        return positions

    def _assign_layers(self, nodes: List[Dict], edges: List[Dict]) -> List[List[Dict]]:
        """
        Phase 1: Assign nodes to layers using the longest path method.

        Instead of simple depth/path counting, calculates the maximum depth of each node's
        subtree. This ensures longer branches rise higher, creating a proper hierarchical
        tree layout where folders with more descendants are positioned above leaf nodes.

        Algorithm:
        1. Build a child map from edges (parent -> children)
        2. Recursively compute max_depth for each node:
           - Leaf nodes: max_depth = 0
           - Internal nodes: max_depth = 1 + max(children's depths)
        3. Assign layers based on max_depth (highest values = topmost layers)
        """
        # Build child map: node_id -> [child_ids]
        children_map = defaultdict(list)
        node_dict = {node['id']: node for node in nodes}

        for edge in edges:
            source = edge.get('source') or edge.get('from')
            target = edge.get('target') or edge.get('to')
            if source and target:
                children_map[source].append(target)

        # Cache for computed depths
        depth_cache = {}

        def compute_max_depth(node_id: str) -> int:
            """
            Recursively compute the maximum depth of a node's subtree.

            Returns:
                0 for leaf nodes
                1 + max(children_depths) for internal nodes
            """
            if node_id in depth_cache:
                return depth_cache[node_id]

            children = children_map.get(node_id, [])

            if not children:
                # Leaf node
                depth = 0
            else:
                # Internal node: max depth is 1 + max depth of children
                max_child_depth = max(compute_max_depth(child_id) for child_id in children)
                depth = 1 + max_child_depth

            depth_cache[node_id] = depth
            return depth

        # Compute layer (max_depth) for each node
        layer_map = defaultdict(list)
        for node in nodes:
            layer = compute_max_depth(node['id'])
            layer_map[layer].append(node)

        # Build ordered layer list from highest depth to lowest (top to bottom in visualization)
        if not layer_map:
            return []

        max_layer = max(layer_map.keys())
        # Reverse the order: highest depths first (will appear at top of visualization)
        return [layer_map.get(max_layer - d, []) for d in range(max_layer + 1)]

    def _minimize_crossings(self, layers: List[List[Dict]], edges: List[Dict]) -> List[List[Dict]]:
        """
        Phase 2: Minimize edge crossings using barycenter method.

        Orders nodes in each layer to minimize the number of edge crossings
        with the previous layer.
        """
        # Build parent map: child_id -> [parent_ids]
        parent_map = defaultdict(list)
        for edge in edges:
            source = edge.get('source') or edge.get('from')
            target = edge.get('target') or edge.get('to')
            if target and source:
                parent_map[target].append(source)

        # Track positions for barycenter calculation
        positions = {}
        ordered = []

        for level_idx, layer in enumerate(layers):
            if level_idx == 0:
                # First layer: sort alphabetically
                sorted_layer = sorted(layer, key=lambda n: n.get('name', ''))
                for i, node in enumerate(sorted_layer):
                    positions[node['id']] = i
                ordered.append(sorted_layer)
                continue

            # Calculate barycenter for each node
            barycenters = []
            for node in layer:
                parents = parent_map.get(node['id'], [])
                if parents:
                    bc = sum(positions.get(p, 0) for p in parents) / len(parents)
                else:
                    bc = 0
                barycenters.append((node, bc))

            # Sort by barycenter
            barycenters.sort(key=lambda x: x[1])
            sorted_layer = [item[0] for item in barycenters]

            # Update positions
            for i, node in enumerate(sorted_layer):
                positions[node['id']] = i

            ordered.append(sorted_layer)

        return ordered

    def _calculate_coordinates(self, layers: List[List[Dict]]) -> Dict[str, NodePosition]:
        """
        Phase 3: Calculate X, Y, Z coordinates for each node.

        - Y increases with layer (depth)
        - X is centered around 0 for each layer
        - Z is 0 (can be used for duplicates later)
        """
        positions = {}

        for level_idx, layer in enumerate(layers):
            y = self.BASE_Y + level_idx * self.LAYER_HEIGHT

            # Calculate total width and starting X
            total_width = (len(layer) - 1) * self.NODE_SPACING if layer else 0
            start_x = -total_width / 2

            for node_idx, node in enumerate(layer):
                positions[node['id']] = NodePosition(
                    x=start_x + node_idx * self.NODE_SPACING,
                    y=y,
                    z=0.0,
                    layer=level_idx,
                    index=node_idx
                )

        return positions

    def _apply_repulsion(self, positions: Dict[str, NodePosition], iterations: int = 3):
        """
        Phase 4: Apply repulsion forces for organic look.

        Nodes in the same layer push each other apart if too close.
        """
        k = 100.0  # Repulsion strength

        pos_list = list(positions.items())

        for _ in range(iterations):
            for i, (id1, pos1) in enumerate(pos_list):
                for j, (id2, pos2) in enumerate(pos_list):
                    if i >= j:
                        continue
                    if pos1.layer != pos2.layer:
                        continue

                    dx = pos1.x - pos2.x
                    dist = abs(dx)

                    if 0 < dist < k:
                        force = (k - dist) / dist * 0.3
                        pos1.x += math.copysign(force, dx)
                        pos2.x -= math.copysign(force, dx)


def calculate_vetka_layout(nodes: List[Dict], edges: List[Dict], options: Dict = None) -> Dict[str, Dict]:
    """
    Main function to calculate VETKA layout.

    Args:
        nodes: List of node dictionaries
        edges: List of edge dictionaries
        options: Optional layout parameters:
            - layer_height: Vertical distance between layers (default: 80.0)
            - node_spacing: Horizontal distance between nodes (default: 120.0)
            - base_y: Starting Y position (default: 50.0)

    Returns:
        Dictionary mapping node IDs to position dictionaries
    """
    options = options or {}

    layout = VETKASugiyamaLayout(
        layer_height=options.get('layer_height', 80.0),
        node_spacing=options.get('node_spacing', 120.0),
        base_y=options.get('base_y', 50.0)
    )

    positions = layout.calculate(nodes, edges)

    return {node_id: pos.to_dict() for node_id, pos in positions.items()}
