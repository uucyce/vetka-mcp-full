"""
VETKA Knowledge Graph Layout Engine.
Phase 17: Semantic layout based on knowledge levels.

Adapts Sugiyama algorithm for Knowledge Graphs:
- Y-axis = knowledge_level (not directory depth!)
- Layers organized by semantic progression
- Same 3-step process: layers -> crossing reduction -> coordinates

Based on Grok Topic 2 + existing Sugiyama implementation.

Date: December 21, 2025

@status: active
@phase: 96
@depends: logging, math, typing, dataclasses, collections, networkx
@used_by: src.visualizer.tree_renderer, src.orchestration.kg_extractor
"""

import logging
import math
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from collections import defaultdict
import networkx as nx

logger = logging.getLogger("VETKA_KG_Layout")


@dataclass
class KGPosition:
    """Position for a concept node in knowledge graph mode."""
    x: float
    y: float
    z: float
    angle: float
    layer: int
    knowledge_level: float
    concept_id: str


class KGLayoutEngine:
    """
    Adapt Sugiyama algorithm for Knowledge Graphs.

    Key difference from directory mode:
    - Y-axis = knowledge_level (not depth)
    - Layers organized by semantic progression (0.0 → 1.0)
    - Same crossing reduction and coordinate assignment

    Phases:
    1. Layer Assignment (by knowledge_level)
    2. Crossing Reduction (barycenter method)
    3. Coordinate Assignment (angular distribution)
    4. Soft Repulsion (optional, for organic look)
    """

    # Layout parameters (from Grok + Phase 15)
    LAYER_HEIGHT = 80.0  # Vertical spacing between layers
    NODE_SPACING = 120.0  # Horizontal spacing
    BASE_Y = 50.0  # Starting Y position
    NUM_LAYERS = 10  # Number of knowledge level buckets

    def __init__(
        self,
        layer_height: float = 80.0,
        node_spacing: float = 120.0,
        base_y: float = 50.0,
        num_layers: int = 10
    ):
        """
        Initialize KG layout engine.

        Args:
            layer_height: Vertical distance between layers
            node_spacing: Horizontal distance between nodes
            base_y: Starting Y position for lowest layer
            num_layers: Number of knowledge level buckets (default 10)
        """
        self.LAYER_HEIGHT = layer_height
        self.NODE_SPACING = node_spacing
        self.BASE_Y = base_y
        self.NUM_LAYERS = num_layers

    async def layout_knowledge_graph(
        self,
        kg: Dict[str, Any],
        vetka_tree: Optional[Dict] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Complete KG layout pipeline using adapted Sugiyama.

        Args:
            kg: Knowledge graph from KGExtractor with keys:
                - concepts: List of Concept objects
                - edges: List of KnowledgeEdge objects
                - levels: Dict of concept_id -> knowledge_level
                - graph: NetworkX DiGraph
            vetka_tree: Original VETKA tree (optional, for reference)

        Returns:
            Dictionary mapping concept_id to position dict:
            {
                'concept_id': {
                    'x': float,
                    'y': float,
                    'z': float,
                    'angle': float,
                    'layer': int,
                    'knowledge_level': float
                }
            }
        """
        logger.info("Starting KG layout computation")

        # Extract data
        concepts = kg.get('concepts', [])
        edges = kg.get('edges', [])
        levels = kg.get('levels', {})
        graph = kg.get('graph')

        if not concepts:
            logger.warning("No concepts in KG - returning empty layout")
            return {}

        # Phase 1: Layer assignment by knowledge_level
        layers = await self._assign_layers_by_level(concepts, levels)
        logger.info(f"Assigned {len(concepts)} concepts to {len(layers)} layers")

        # Phase 2: Crossing reduction
        if graph:
            layers = await self._reduce_crossings(layers, graph)
            logger.info("Crossing reduction complete")

        # Phase 3: Coordinate assignment
        positions = await self._assign_coordinates(layers, levels)
        logger.info(f"Assigned coordinates to {len(positions)} concepts")

        # Phase 4 (optional): Soft repulsion
        positions = await self._apply_soft_repulsion(positions, layers)

        return positions

    async def _assign_layers_by_level(
        self,
        concepts: List[Any],
        levels: Dict[str, float]
    ) -> List[List[str]]:
        """
        Organize concepts into layers by knowledge_level.

        Instead of directory depth, use semantic level:
        - Layer 0: level 0.0-0.1 (basics)
        - Layer 1: level 0.1-0.2
        - ...
        - Layer 9: level 0.9-1.0 (advanced)

        Args:
            concepts: List of Concept objects
            levels: Dict of concept_id -> knowledge_level

        Returns:
            List of layers, each layer is list of concept IDs
        """
        # Create layer buckets
        layers = [[] for _ in range(self.NUM_LAYERS)]

        for concept in concepts:
            concept_id = concept.id if hasattr(concept, 'id') else str(concept)
            level = levels.get(concept_id, 0.5)

            # Compute bucket (0 to NUM_LAYERS-1)
            bucket = int(level * self.NUM_LAYERS)
            bucket = min(bucket, self.NUM_LAYERS - 1)  # Handle level=1.0

            layers[bucket].append(concept_id)

        # Remove empty layers and re-index
        non_empty_layers = [layer for layer in layers if layer]

        logger.debug(f"Layer distribution: {[len(l) for l in non_empty_layers]}")

        return non_empty_layers

    async def _reduce_crossings(
        self,
        layers: List[List[str]],
        graph: nx.DiGraph
    ) -> List[List[str]]:
        """
        Barycenter method for crossing reduction.

        For each layer (top to bottom):
        1. Find prerequisites (incoming edges from previous layer)
        2. Calculate barycenter (average position of prerequisites)
        3. Sort by barycenter

        This minimizes edge crossings and visually groups related concepts.

        Args:
            layers: List of layers (each layer is list of concept IDs)
            graph: NetworkX DiGraph with prerequisite edges

        Returns:
            Layers with nodes reordered to minimize crossings
        """
        if not graph:
            return layers

        # Iterate from second layer to last
        for layer_idx in range(1, len(layers)):
            current_layer = layers[layer_idx]
            previous_layer = layers[layer_idx - 1]

            # Build position map for previous layer
            prev_positions = {
                concept_id: idx
                for idx, concept_id in enumerate(previous_layer)
            }

            # Calculate barycenters
            barycenters = {}

            for concept_id in current_layer:
                # Find prerequisites in previous layer
                if concept_id in graph:
                    predecessors = list(graph.predecessors(concept_id))
                    predecessors_in_prev = [
                        p for p in predecessors if p in prev_positions
                    ]

                    if predecessors_in_prev:
                        # Average position of prerequisites
                        avg_pos = sum(
                            prev_positions[p] for p in predecessors_in_prev
                        ) / len(predecessors_in_prev)
                        barycenters[concept_id] = avg_pos
                    else:
                        barycenters[concept_id] = len(previous_layer) / 2
                else:
                    barycenters[concept_id] = len(previous_layer) / 2

            # Sort by barycenter
            current_layer.sort(key=lambda c: barycenters.get(c, 0))
            layers[layer_idx] = current_layer

        return layers

    async def _assign_coordinates(
        self,
        layers: List[List[str]],
        levels: Dict[str, float]
    ) -> Dict[str, Dict[str, float]]:
        """
        Assign 3D coordinates to concepts.

        Y-axis: Based on layer (semantic progression)
        X-axis: Angular distribution (spread out horizontally)
        Z-axis: 0 (or use for variants later)

        Args:
            layers: Ordered layers of concept IDs
            levels: Knowledge levels for each concept

        Returns:
            Dictionary of concept_id -> position dict
        """
        positions = {}

        max_depth = len(layers)

        for layer_idx, layer in enumerate(layers):
            # Y position (semantic level)
            Y = self.BASE_Y + layer_idx * self.LAYER_HEIGHT

            num_nodes = len(layer)

            # Angular spread (wider at bottom, narrower at top)
            # Inverted from directory mode: basics spread wide
            spread_factor = 1.0 - (layer_idx / max_depth)
            max_angle = 180 * spread_factor

            for node_idx, concept_id in enumerate(layer):
                # Calculate angle
                if num_nodes > 1:
                    # Spread from -max_angle/2 to +max_angle/2
                    angle_deg = -max_angle/2 + node_idx * (max_angle / (num_nodes - 1))
                else:
                    angle_deg = 0

                # Convert to X position
                angle_rad = math.radians(angle_deg)
                radius = 100  # Base radius
                X = math.sin(angle_rad) * radius

                # Z position (for now, flat)
                Z = 0

                # Store position
                positions[concept_id] = {
                    'x': X,
                    'y': Y,
                    'z': Z,
                    'angle': angle_deg,
                    'layer': layer_idx,
                    'knowledge_level': levels.get(concept_id, 0.5)
                }

        return positions

    async def _apply_soft_repulsion(
        self,
        positions: Dict[str, Dict[str, float]],
        layers: List[List[str]],
        iterations: int = 3
    ) -> Dict[str, Dict[str, float]]:
        """
        Apply soft repulsion forces for organic look.

        Nodes in same layer push each other apart if too close.

        Args:
            positions: Current positions
            layers: Layer assignments
            iterations: Number of repulsion iterations

        Returns:
            Adjusted positions
        """
        k = 100.0  # Repulsion strength

        for _ in range(iterations):
            for layer in layers:
                # Only apply within each layer
                for i, id1 in enumerate(layer):
                    for id2 in layer[i+1:]:
                        pos1 = positions[id1]
                        pos2 = positions[id2]

                        # Distance in X
                        dx = pos1['x'] - pos2['x']
                        dist = abs(dx)

                        # Repulsion if too close
                        if 0 < dist < k:
                            force = (k - dist) / dist * 0.3
                            pos1['x'] += math.copysign(force, dx)
                            pos2['x'] -= math.copysign(force, dx)

        return positions

    def calculate_optimal_layer_height(
        self,
        max_depth: int,
        total_nodes: int,
        screen_height: int = 1080
    ) -> float:
        """
        Calculate optimal layer height based on Grok Topic 1 formula.

        Formula:
        layer_height = base_height * (screen_height / 1080) /
                       (depth_factor * (1 + 0.3 * density_factor))

        Args:
            max_depth: Maximum depth (number of layers)
            total_nodes: Total number of nodes
            screen_height: Screen height in pixels

        Returns:
            Optimal layer height (clamped to 50-200px)
        """
        base_height = 80.0
        depth_factor = max_depth
        density_factor = 1 + math.log10(total_nodes / 100)

        layer_height = base_height * (screen_height / 1080) / (
            depth_factor * (1 + 0.3 * density_factor)
        )

        # Clamp to reasonable range
        return max(50, min(200, layer_height))


# Example usage
if __name__ == "__main__":
    import asyncio
    import sys
    from pathlib import Path

    # Add project root to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    logging.basicConfig(level=logging.INFO)

    async def test_kg_layout():
        from src.orchestration.kg_extractor import KGExtractor

        # Create test KG
        extractor = KGExtractor()

        test_tree = {
            'node1': {'path': 'src/orchestration/cam_engine.py'},
            'node2': {'path': 'src/visualizer/procrustes_interpolation.py'},
            'node3': {'path': 'docs/PHASE_16_SUMMARY.md'}
        }

        kg = await extractor.extract_knowledge_graph(test_tree)

        # Create layout
        layout_engine = KGLayoutEngine()
        positions = await layout_engine.layout_knowledge_graph(kg)

        print(f"\nKG Layout Summary:")
        print(f"  Positioned {len(positions)} concepts")

        # Show sample positions
        print(f"\nSample positions:")
        for concept_id, pos in list(positions.items())[:5]:
            print(f"  {concept_id}")
            print(f"    Level: {pos['knowledge_level']:.2f}")
            print(f"    Layer: {pos['layer']}")
            print(f"    Y: {pos['y']:.1f}")

    asyncio.run(test_kg_layout())
