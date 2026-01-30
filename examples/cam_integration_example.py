"""
VETKA Phase 16 CAM Integration Example
Demonstrates how to integrate CAM engine with existing VETKA components

This example shows:
1. How to initialize CAM engine with MemoryManager
2. How to handle new artifacts from scanner
3. How to integrate with layout engine
4. How to track metrics
5. How to emit Socket.IO events (stub)

Date: December 21, 2025
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestration.cam_engine import VETKACAMEngine, VETKANode
from src.orchestration.memory_manager import MemoryManager
from src.visualizer.position_calculator import VETKASugiyamaLayout
from src.visualizer.procrustes_interpolation import (
    ProcrustesInterpolator,
    LayoutPosition
)
from src.monitoring.cam_metrics import get_cam_metrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class VETKAWithCAM:
    """
    Example integration of VETKA components with CAM engine.

    This class shows how to wire together:
    - CAM Engine (dynamic tree operations)
    - Memory Manager (triple write storage)
    - Layout Engine (Sugiyama positioning)
    - Metrics (performance tracking)
    """

    def __init__(self):
        """Initialize all VETKA components."""
        # Initialize memory manager
        self.memory_manager = MemoryManager(
            weaviate_url="http://localhost:8080",
            qdrant_url="http://localhost:6333",
            changelog_path="data/changelog.jsonl",
            embedding_model="auto"
        )

        # Initialize layout engine
        self.layout_engine = VETKASugiyamaLayout(
            layer_height=80.0,
            node_spacing=120.0,
            base_y=50.0
        )

        # Initialize CAM engine
        self.cam_engine = VETKACAMEngine(
            memory_manager=self.memory_manager,
            layout_engine=self.layout_engine
        )

        # Initialize metrics tracker
        self.metrics = get_cam_metrics()

        # Procrustes interpolator for smooth transitions
        self.interpolator = ProcrustesInterpolator(
            animation_duration=0.75,
            collision_threshold=30.0,
            easing='ease-in-out-cubic'
        )

        logging.info("VETKA with CAM initialized")

    async def handle_new_file(self, file_path: str, content: str):
        """
        Handle detection of new file (would be called by scanner).

        Args:
            file_path: Path to new file
            content: File content
        """
        logging.info(f"Processing new file: {file_path}")

        # Prepare metadata
        metadata = {
            'name': Path(file_path).name,
            'type': self._detect_file_type(file_path),
            'size': len(content),
            'content': content,
            'parent': str(Path(file_path).parent),
            'depth': len(Path(file_path).parts) - 1
        }

        # Track operation time
        import time
        start_time = time.time()

        # CAM branching operation
        operation = await self.cam_engine.handle_new_artifact(
            artifact_path=file_path,
            metadata=metadata
        )

        duration_ms = (time.time() - start_time) * 1000

        # Track metrics
        self.metrics.track_branch_creation(file_path, duration_ms)

        # Save to memory manager
        if operation.success:
            self.memory_manager.triple_write({
                'workflow_id': 'cam_integration',
                'type': 'cam_operation',
                'operation_type': operation.operation_type,
                'node_ids': operation.node_ids,
                'file_path': file_path,
                'speaker': 'cam_engine'
            })

        # Emit Socket.IO event (stub)
        self._emit_socketio('cam_operation', {
            'type': operation.operation_type,
            'node_ids': operation.node_ids,
            'duration_ms': duration_ms,
            'success': operation.success
        })

        logging.info(
            f"CAM operation complete: {operation.operation_type} "
            f"in {duration_ms:.0f}ms"
        )

        return operation

    async def run_periodic_pruning(self):
        """
        Run periodic pruning (would be scheduled hourly).
        """
        logging.info("Running periodic pruning")

        # Identify candidates
        candidates = await self.cam_engine.prune_low_entropy(threshold=0.2)

        # Emit to frontend for user confirmation
        self._emit_socketio('prune_candidates', {
            'candidates': [
                {
                    'node_id': nid,
                    'name': self.cam_engine.nodes[nid].name,
                    'score': self.cam_engine.nodes[nid].activation_score
                }
                for nid in candidates
            ]
        })

        logging.info(f"Found {len(candidates)} prune candidates")
        return candidates

    async def merge_similar_branches(self):
        """
        Find and merge similar branches.
        """
        logging.info("Searching for merge candidates")

        # Find similar subtrees
        merged_pairs = await self.cam_engine.merge_similar_subtrees(
            threshold=0.92
        )

        # Track metrics
        for old_id, merged_id in merged_pairs:
            self.metrics.track_merge_accuracy(
                proposed_merge=True,
                user_accepted=True  # Auto-accept in this example
            )

        # Emit results
        self._emit_socketio('merge_complete', {
            'merged_pairs': merged_pairs,
            'count': len(merged_pairs)
        })

        logging.info(f"Merged {len(merged_pairs)} branch pairs")
        return merged_pairs

    async def recalculate_layout(self, reason: str = "structure_changed"):
        """
        Recalculate layout with smooth Procrustes transition.

        Args:
            reason: Reason for layout recalculation
        """
        logging.info(f"Recalculating layout: {reason}")

        # Get old positions (from CAM engine)
        accommodation = await self.cam_engine.accommodate_layout(reason=reason)

        old_pos_dict = accommodation.get('old_positions', {})
        new_pos_dict = accommodation.get('new_positions', {})

        if old_pos_dict and new_pos_dict:
            # Convert to LayoutPosition objects
            old_positions = {
                nid: LayoutPosition(p['x'], p['y'], p['z'])
                for nid, p in old_pos_dict.items()
            }
            new_positions = {
                nid: LayoutPosition(p['x'], p['y'], p['z'])
                for nid, p in new_pos_dict.items()
            }

            # Generate animation frames
            frames = self.interpolator.generate_animation_frames(
                old_positions=old_positions,
                new_positions=new_positions,
                fps=60,
                resolve_collisions=True
            )

            # Track metrics
            self.metrics.track_accommodation_fps(60.0)

            # Calculate collision rate
            from src.visualizer.procrustes_interpolation import calculate_collision_rate
            collision_rate = calculate_collision_rate(frames)
            self.metrics.track_collision_rate(
                total_frames=len(frames),
                collision_frames=int(len(frames) * collision_rate)
            )

            # Emit animation frames to frontend
            for frame_idx, frame_positions in enumerate(frames):
                self._emit_socketio('layout_frame', {
                    'frame': frame_idx,
                    'total_frames': len(frames),
                    'positions': {
                        nid: {'x': pos.x, 'y': pos.y, 'z': pos.z}
                        for nid, pos in frame_positions.items()
                    }
                })

            logging.info(f"Generated {len(frames)} animation frames")

    def add_user_query(self, query: str):
        """
        Add user query to history for activation scoring.

        Args:
            query: User query text
        """
        self.cam_engine.add_query_to_history(query)
        logging.info(f"Added query to history: {query[:50]}...")

    def get_metrics_summary(self):
        """Get CAM performance metrics summary."""
        summary = self.metrics.get_summary()
        goals = self.metrics.check_goals()

        logging.info("CAM Metrics Summary:")
        logging.info(f"  Branching: {summary['branching']['avg']:.0f}ms avg")
        logging.info(f"  Goals met: {goals}")

        return summary

    def _detect_file_type(self, file_path: str) -> str:
        """Detect file type from extension."""
        suffix = Path(file_path).suffix.lower()
        type_map = {
            '.md': 'markdown',
            '.txt': 'text',
            '.py': 'python',
            '.js': 'javascript',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml'
        }
        return type_map.get(suffix, 'unknown')

    def _emit_socketio(self, event: str, data: dict):
        """
        Emit Socket.IO event (stub implementation).

        In real implementation, this would use Flask-SocketIO.

        Args:
            event: Event name
            data: Event data
        """
        logging.debug(f"[Socket.IO] {event}: {data}")
        # In real implementation:
        # socketio.emit(event, data, namespace='/vetka')


async def main():
    """
    Example usage of VETKA with CAM integration.
    """
    print("=" * 60)
    print("VETKA Phase 16 CAM Integration Example")
    print("=" * 60)

    # Initialize VETKA with CAM
    vetka = VETKAWithCAM()

    # Simulate adding new files
    print("\n1. Adding new files...")
    await vetka.handle_new_file(
        file_path="/docs/VETKA_Architecture.md",
        content="# VETKA Architecture\n\nVETKA is a tree-based knowledge system..."
    )

    await vetka.handle_new_file(
        file_path="/docs/CAM_Implementation.md",
        content="# CAM Implementation\n\nConstructivist Agentic Memory for VETKA..."
    )

    await vetka.handle_new_file(
        file_path="/docs/Phase_16_Guide.md",
        content="# Phase 16 Guide\n\nIntegrating CAM into VETKA..."
    )

    # Simulate user queries
    print("\n2. Adding user queries...")
    vetka.add_user_query("VETKA architecture overview")
    vetka.add_user_query("How does CAM work?")
    vetka.add_user_query("Phase 16 implementation details")

    # Run pruning
    print("\n3. Running periodic pruning...")
    candidates = await vetka.run_periodic_pruning()
    print(f"   Found {len(candidates)} candidates for pruning")

    # Merge similar branches
    print("\n4. Merging similar branches...")
    merged = await vetka.merge_similar_branches()
    print(f"   Merged {len(merged)} branch pairs")

    # Recalculate layout
    print("\n5. Recalculating layout with Procrustes...")
    await vetka.recalculate_layout(reason="example_complete")

    # Get metrics
    print("\n6. Performance Metrics:")
    summary = vetka.get_metrics_summary()

    print("\n" + "=" * 60)
    print("CAM Integration Example Complete!")
    print("=" * 60)


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
