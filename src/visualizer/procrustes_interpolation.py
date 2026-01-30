"""
VETKA Procrustes Interpolation - Smooth Layout Transitions.
Phase 16: Accommodation with Procrustes Analysis.

Implements smooth transitions between tree layouts using Procrustes alignment.
Based on Grok Topic 5 findings: minimize rotation + scaling + translation
to create natural, smooth animations when tree structure changes.

Mathematical formulation:
    min ||R*X_new + t - X_old||^2
where:
    R = rotation matrix
    t = translation vector
    X_old = old node positions
    X_new = new node positions

Date: December 21, 2025

@status: active
@phase: 96
@depends: logging, numpy, typing, dataclasses, scipy.spatial, scipy.linalg
@used_by: src.visualizer.tree_renderer, src.api.routes.tree_routes
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from scipy.spatial import procrustes
from scipy.linalg import orthogonal_procrustes

logger = logging.getLogger("VETKA_Procrustes")


@dataclass
class LayoutPosition:
    """3D position for a node."""
    x: float
    y: float
    z: float

    def to_array(self) -> np.ndarray:
        """Convert to numpy array."""
        return np.array([self.x, self.y, self.z])

    @staticmethod
    def from_array(arr: np.ndarray) -> 'LayoutPosition':
        """Create from numpy array."""
        return LayoutPosition(x=arr[0], y=arr[1], z=arr[2])


@dataclass
class ProcrustesAlignment:
    """
    Result of Procrustes alignment.

    Attributes:
        rotation: Rotation matrix (3x3)
        translation: Translation vector (3D)
        scale: Scale factor
        aligned_positions: New positions after alignment
        residual: Alignment residual (measure of fit quality)
    """
    rotation: np.ndarray
    translation: np.ndarray
    scale: float
    aligned_positions: Dict[str, LayoutPosition]
    residual: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'rotation': self.rotation.tolist(),
            'translation': self.translation.tolist(),
            'scale': float(self.scale),
            'residual': float(self.residual),
            'aligned_positions': {
                node_id: {'x': pos.x, 'y': pos.y, 'z': pos.z}
                for node_id, pos in self.aligned_positions.items()
            }
        }


class ProcrustesInterpolator:
    """
    Procrustes-based smooth interpolation for layout transitions.

    Ensures minimal visual disruption when tree structure changes by:
    1. Aligning new layout to old layout using Procrustes analysis
    2. Computing smooth interpolation path
    3. Detecting and resolving collisions
    """

    def __init__(
        self,
        animation_duration: float = 0.75,
        collision_threshold: float = 30.0,
        easing: str = 'ease-in-out-cubic'
    ):
        """
        Initialize Procrustes interpolator.

        Args:
            animation_duration: Animation duration in seconds (default 0.75s)
            collision_threshold: Minimum distance between nodes (default 30px)
            easing: Easing function name
        """
        self.animation_duration = animation_duration
        self.collision_threshold = collision_threshold
        self.easing = easing

    def align_layouts(
        self,
        old_positions: Dict[str, LayoutPosition],
        new_positions: Dict[str, LayoutPosition]
    ) -> ProcrustesAlignment:
        """
        Align new layout to old layout using Procrustes analysis.

        Finds optimal rotation, translation, and scale to minimize distance
        between old and new positions.

        Args:
            old_positions: Dictionary of node_id -> old position
            new_positions: Dictionary of node_id -> new position

        Returns:
            ProcrustesAlignment with transformation parameters
        """
        # Find common nodes (nodes that exist in both layouts)
        common_nodes = set(old_positions.keys()) & set(new_positions.keys())

        if len(common_nodes) < 2:
            # Not enough common nodes for alignment
            logger.warning(f"Only {len(common_nodes)} common nodes - skipping alignment")
            return ProcrustesAlignment(
                rotation=np.eye(3),
                translation=np.zeros(3),
                scale=1.0,
                aligned_positions=new_positions,
                residual=0.0
            )

        # Convert to matrices (N x 3)
        common_nodes_list = sorted(common_nodes)  # Ensure consistent ordering
        old_matrix = np.array([old_positions[nid].to_array() for nid in common_nodes_list])
        new_matrix = np.array([new_positions[nid].to_array() for nid in common_nodes_list])

        # Center both matrices
        old_center = np.mean(old_matrix, axis=0)
        new_center = np.mean(new_matrix, axis=0)

        old_centered = old_matrix - old_center
        new_centered = new_matrix - new_center

        # Compute scale
        old_scale = np.sqrt(np.sum(old_centered ** 2))
        new_scale = np.sqrt(np.sum(new_centered ** 2))
        scale = old_scale / new_scale if new_scale > 0 else 1.0

        # Scale new positions
        new_scaled = new_centered * scale

        # Compute rotation using orthogonal Procrustes
        rotation, _ = orthogonal_procrustes(new_scaled, old_centered)

        # Compute residual
        transformed = new_scaled @ rotation.T
        residual = np.sqrt(np.mean((transformed - old_centered) ** 2))

        # Apply transformation to ALL new positions (not just common ones)
        aligned_positions = {}
        for node_id, pos in new_positions.items():
            # Center, scale, rotate, uncenter
            centered = pos.to_array() - new_center
            scaled = centered * scale
            rotated = rotation @ scaled
            final = rotated + old_center

            aligned_positions[node_id] = LayoutPosition.from_array(final)

        logger.info(
            f"Procrustes alignment: scale={scale:.3f}, residual={residual:.3f}, "
            f"common_nodes={len(common_nodes)}"
        )

        return ProcrustesAlignment(
            rotation=rotation,
            translation=old_center - new_center,
            scale=scale,
            aligned_positions=aligned_positions,
            residual=residual
        )

    def interpolate(
        self,
        old_positions: Dict[str, LayoutPosition],
        new_positions: Dict[str, LayoutPosition],
        t: float
    ) -> Dict[str, LayoutPosition]:
        """
        Interpolate between old and new positions at time t.

        Args:
            old_positions: Starting positions
            new_positions: Target positions (should be aligned)
            t: Interpolation parameter (0.0 = old, 1.0 = new)

        Returns:
            Dictionary of interpolated positions
        """
        # Apply easing function
        t_eased = self._ease(t)

        interpolated = {}
        all_nodes = set(old_positions.keys()) | set(new_positions.keys())

        for node_id in all_nodes:
            old_pos = old_positions.get(node_id)
            new_pos = new_positions.get(node_id)

            if old_pos and new_pos:
                # Existing node - interpolate
                old_arr = old_pos.to_array()
                new_arr = new_pos.to_array()
                interp_arr = old_arr + (new_arr - old_arr) * t_eased
                interpolated[node_id] = LayoutPosition.from_array(interp_arr)

            elif new_pos:
                # New node - fade in
                opacity_factor = t_eased
                interp_arr = new_pos.to_array()
                interpolated[node_id] = LayoutPosition.from_array(interp_arr)
                # Note: opacity would be handled separately in rendering

            elif old_pos:
                # Removed node - fade out
                opacity_factor = 1.0 - t_eased
                interp_arr = old_pos.to_array()
                interpolated[node_id] = LayoutPosition.from_array(interp_arr)

        return interpolated

    def detect_collisions(
        self,
        positions: Dict[str, LayoutPosition]
    ) -> List[Tuple[str, str]]:
        """
        Detect collisions between nodes.

        Args:
            positions: Node positions

        Returns:
            List of (node_id_a, node_id_b) collision pairs
        """
        collisions = []
        node_ids = list(positions.keys())

        for i, id_a in enumerate(node_ids):
            for id_b in node_ids[i+1:]:
                pos_a = positions[id_a].to_array()
                pos_b = positions[id_b].to_array()

                distance = np.linalg.norm(pos_a - pos_b)

                if distance < self.collision_threshold:
                    collisions.append((id_a, id_b))

        return collisions

    def resolve_collisions(
        self,
        positions: Dict[str, LayoutPosition],
        max_iterations: int = 5
    ) -> Dict[str, LayoutPosition]:
        """
        Resolve collisions using force-directed approach.

        Args:
            positions: Node positions with collisions
            max_iterations: Maximum iterations for collision resolution

        Returns:
            Positions with collisions resolved
        """
        positions_copy = {nid: LayoutPosition(p.x, p.y, p.z) for nid, p in positions.items()}

        for iteration in range(max_iterations):
            collisions = self.detect_collisions(positions_copy)

            if not collisions:
                break  # No collisions

            # Apply repulsion forces
            for id_a, id_b in collisions:
                pos_a = positions_copy[id_a].to_array()
                pos_b = positions_copy[id_b].to_array()

                # Vector from B to A
                delta = pos_a - pos_b
                distance = np.linalg.norm(delta)

                if distance < 1e-6:
                    # Nodes at exact same position - apply random offset
                    delta = np.random.randn(3) * 0.1
                    distance = np.linalg.norm(delta)

                # Repulsion force (stronger when closer)
                force_magnitude = (self.collision_threshold - distance) * 0.5
                force = (delta / distance) * force_magnitude

                # Apply force (push apart)
                positions_copy[id_a].x += force[0]
                positions_copy[id_a].y += force[1]
                positions_copy[id_a].z += force[2]

                positions_copy[id_b].x -= force[0]
                positions_copy[id_b].y -= force[1]
                positions_copy[id_b].z -= force[2]

            logger.debug(f"Collision resolution iteration {iteration + 1}: {len(collisions)} collisions")

        final_collisions = self.detect_collisions(positions_copy)
        if final_collisions:
            logger.warning(f"Could not resolve all collisions: {len(final_collisions)} remaining")

        return positions_copy

    def generate_animation_frames(
        self,
        old_positions: Dict[str, LayoutPosition],
        new_positions: Dict[str, LayoutPosition],
        fps: int = 60,
        resolve_collisions: bool = True
    ) -> List[Dict[str, LayoutPosition]]:
        """
        Generate animation frames for smooth transition.

        Args:
            old_positions: Starting positions
            new_positions: Target positions
            fps: Target frames per second
            resolve_collisions: Whether to resolve collisions in each frame

        Returns:
            List of position dictionaries (one per frame)
        """
        # First, align new positions to old positions
        alignment = self.align_layouts(old_positions, new_positions)
        aligned_new = alignment.aligned_positions

        # Calculate number of frames
        num_frames = int(self.animation_duration * fps)
        frames = []

        for frame_idx in range(num_frames + 1):
            t = frame_idx / num_frames
            frame_positions = self.interpolate(old_positions, aligned_new, t)

            if resolve_collisions:
                frame_positions = self.resolve_collisions(frame_positions, max_iterations=2)

            frames.append(frame_positions)

        logger.info(
            f"Generated {len(frames)} animation frames "
            f"({fps} FPS, {self.animation_duration}s duration)"
        )

        return frames

    def _ease(self, t: float) -> float:
        """
        Apply easing function to interpolation parameter.

        Args:
            t: Linear interpolation parameter (0.0 to 1.0)

        Returns:
            Eased parameter
        """
        if self.easing == 'linear':
            return t
        elif self.easing == 'ease-in-out-cubic':
            # Cubic ease-in-out
            if t < 0.5:
                return 4 * t * t * t
            else:
                return 1 - pow(-2 * t + 2, 3) / 2
        elif self.easing == 'ease-out-quad':
            return 1 - (1 - t) * (1 - t)
        elif self.easing == 'ease-in-quad':
            return t * t
        else:
            # Default to ease-in-out-cubic
            if t < 0.5:
                return 4 * t * t * t
            else:
                return 1 - pow(-2 * t + 2, 3) / 2


def calculate_collision_rate(
    frames: List[Dict[str, LayoutPosition]],
    collision_threshold: float = 30.0
) -> float:
    """
    Calculate collision rate across animation frames.

    Args:
        frames: List of position frames
        collision_threshold: Distance threshold for collisions

    Returns:
        Collision rate (0.0 to 1.0)
    """
    interpolator = ProcrustesInterpolator(collision_threshold=collision_threshold)

    frames_with_collisions = 0
    for frame_positions in frames:
        collisions = interpolator.detect_collisions(frame_positions)
        if collisions:
            frames_with_collisions += 1

    return frames_with_collisions / len(frames) if frames else 0.0


# Example usage
if __name__ == "__main__":
    # Test Procrustes interpolation
    logging.basicConfig(level=logging.INFO)

    # Create sample positions
    old_pos = {
        'a': LayoutPosition(0, 0, 0),
        'b': LayoutPosition(100, 0, 0),
        'c': LayoutPosition(50, 100, 0)
    }

    new_pos = {
        'a': LayoutPosition(10, 10, 0),
        'b': LayoutPosition(110, 10, 0),
        'c': LayoutPosition(60, 110, 0),
        'd': LayoutPosition(80, 60, 0)  # New node
    }

    interpolator = ProcrustesInterpolator(animation_duration=0.75)

    # Generate animation
    frames = interpolator.generate_animation_frames(old_pos, new_pos, fps=60)

    print(f"Generated {len(frames)} frames")
    print(f"Collision rate: {calculate_collision_rate(frames):.1%}")
