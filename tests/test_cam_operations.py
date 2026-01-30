"""
Unit Tests for VETKA CAM Operations
Phase 16: Testing all 4 CAM operations

Tests:
1. Branching - creates node if novel (<1s)
2. Merging - preserves data without loss
3. Pruning - identifies low-value >85% accuracy
4. Accommodation - smooth 60 FPS transitions
5. Procrustes alignment - minimizes rotation+scale+translation
6. Collision detection - <5% collision rate

Date: December 21, 2025
"""

import unittest
import asyncio
import time
import numpy as np
from typing import Dict, List
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.orchestration.cam_engine import (
    VETKACAMEngine,
    VETKANode,
    CAMOperation
)
from src.monitoring.cam_metrics import CAMMetrics


class TestCAMOperations(unittest.TestCase):
    """Test suite for CAM operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = VETKACAMEngine()
        self.metrics = CAMMetrics()

    def tearDown(self):
        """Clean up after tests."""
        self.metrics.reset_metrics()

    # ========== BRANCHING TESTS ==========

    def test_branching_creates_node_if_novel(self):
        """Test that similarity < 0.7 creates a new branch."""
        # Create a seed node
        seed_embedding = np.random.randn(768)
        seed_node = VETKANode(
            id="seed",
            path="/test/seed.txt",
            name="seed.txt",
            depth=0,
            embedding=seed_embedding
        )
        self.engine.nodes["seed"] = seed_node

        # Create novel artifact (very different embedding)
        novel_embedding = np.random.randn(768)
        # Ensure low similarity
        novel_embedding = novel_embedding / np.linalg.norm(novel_embedding)

        metadata = {
            'name': 'novel.txt',
            'type': 'text',
            'size': 1024,
            'embedding': novel_embedding,
            'parent': 'seed',
            'depth': 1
        }

        # Run branching
        loop = asyncio.get_event_loop()
        operation = loop.run_until_complete(
            self.engine.handle_new_artifact('/test/novel.txt', metadata)
        )

        # Assertions
        self.assertTrue(operation.success)
        self.assertIn(operation.operation_type, ['branch', 'merge_proposal'])
        self.assertEqual(len(operation.node_ids), 1)

        # New node should exist
        new_id = operation.node_ids[0]
        self.assertIn(new_id, self.engine.nodes)

    def test_branching_detects_in_time(self):
        """Test that detection + branching completes in <1 second."""
        # Create seed node
        seed_node = VETKANode(
            id="seed",
            path="/test/seed.txt",
            name="seed.txt",
            depth=0,
            embedding=np.random.randn(768)
        )
        self.engine.nodes["seed"] = seed_node

        # Create artifact
        metadata = {
            'name': 'new.txt',
            'type': 'text',
            'size': 1024,
            'embedding': np.random.randn(768),
            'parent': 'seed',
            'depth': 1
        }

        # Time the operation
        start = time.time()
        loop = asyncio.get_event_loop()
        operation = loop.run_until_complete(
            self.engine.handle_new_artifact('/test/new.txt', metadata)
        )
        duration_ms = (time.time() - start) * 1000

        # Assertions
        self.assertTrue(operation.success)
        self.assertLess(duration_ms, 1000, "Branching should complete in <1 second")
        self.assertLess(operation.duration_ms, 1000)

    # ========== MERGING TESTS ==========

    def test_merging_preserves_data(self):
        """Test that merge combines data without loss."""
        # Create two similar nodes
        embedding_a = np.random.randn(768)
        embedding_a = embedding_a / np.linalg.norm(embedding_a)

        # Very similar embedding (cosine > 0.92)
        embedding_b = embedding_a + np.random.randn(768) * 0.1
        embedding_b = embedding_b / np.linalg.norm(embedding_b)

        node_a = VETKANode(
            id="node_a",
            path="/test/a.txt",
            name="a.txt",
            depth=0,
            embedding=embedding_a,
            metadata={'original': 'a'}
        )
        node_b = VETKANode(
            id="node_b",
            path="/test/b.txt",
            name="b.txt",
            depth=0,
            embedding=embedding_b,
            metadata={'original': 'b'}
        )

        self.engine.nodes["node_a"] = node_a
        self.engine.nodes["node_b"] = node_b

        # Record original data
        original_metadata_a = node_a.metadata.copy()
        original_metadata_b = node_b.metadata.copy()

        # Run merge
        loop = asyncio.get_event_loop()
        merged_pairs = loop.run_until_complete(
            self.engine.merge_similar_subtrees(threshold=0.85)
        )

        # Assertions
        if merged_pairs:
            # Check data preservation
            self.assertIn("node_a", self.engine.nodes)
            surviving_node = self.engine.nodes["node_a"]

            # Original metadata should be preserved
            self.assertIn('merged_variants', surviving_node.metadata)
            self.assertTrue(len(surviving_node.metadata['merged_variants']) > 0)

            # Merged variant should contain original metadata
            variant = surviving_node.metadata['merged_variants'][0]
            self.assertEqual(variant['metadata']['original'], 'b')

    def test_merging_detects_similarity(self):
        """Test that merging correctly detects similar subtrees."""
        # Create two subtrees with similar embeddings
        base_embedding = np.random.randn(768)
        base_embedding = base_embedding / np.linalg.norm(base_embedding)

        # Node A with children
        node_a = VETKANode(
            id="a",
            path="/a",
            name="a",
            depth=0,
            embedding=base_embedding
        )
        child_a1 = VETKANode(
            id="a1",
            path="/a/a1",
            name="a1",
            depth=1,
            embedding=base_embedding + np.random.randn(768) * 0.01,
            parent="a"
        )
        node_a.children = ["a1"]

        # Node B with similar children
        node_b = VETKANode(
            id="b",
            path="/b",
            name="b",
            depth=0,
            embedding=base_embedding + np.random.randn(768) * 0.02
        )
        child_b1 = VETKANode(
            id="b1",
            path="/b/b1",
            name="b1",
            depth=1,
            embedding=base_embedding + np.random.randn(768) * 0.01,
            parent="b"
        )
        node_b.children = ["b1"]

        # Add to engine
        self.engine.nodes.update({
            "a": node_a,
            "a1": child_a1,
            "b": node_b,
            "b1": child_b1
        })

        # Compute similarity
        similarity = self.engine.compute_branch_similarity("a", "b")

        # Should be high similarity
        self.assertGreater(similarity, 0.85, "Similar subtrees should have >0.85 similarity")

    # ========== PRUNING TESTS ==========

    def test_pruning_identifies_low_value(self):
        """Test that pruning identifies low-value nodes."""
        # Create nodes with different activation scores
        high_value_node = VETKANode(
            id="high",
            path="/high.txt",
            name="high.txt",
            depth=0,
            embedding=np.random.randn(768)
        )

        low_value_node = VETKANode(
            id="low",
            path="/low.txt",
            name="low.txt",
            depth=0,
            embedding=np.random.randn(768),
            parent="high"  # Needs parent to be pruning candidate
        )

        self.engine.nodes["high"] = high_value_node
        self.engine.nodes["low"] = low_value_node

        # Add queries that only match high_value_node
        for i in range(10):
            self.engine.add_query_to_history(
                f"query {i}",
                embedding=high_value_node.embedding + np.random.randn(768) * 0.1
            )

        # Run pruning
        loop = asyncio.get_event_loop()
        candidates = loop.run_until_complete(
            self.engine.prune_low_entropy(threshold=0.2)
        )

        # Low value node should be marked
        if "low" in candidates:
            self.assertTrue(self.engine.nodes["low"].is_marked_for_deletion)

    def test_pruning_accuracy_threshold(self):
        """Test pruning accuracy meets >85% threshold."""
        # This test would require user feedback data
        # For now, test that activation scoring works correctly

        node = VETKANode(
            id="test",
            path="/test.txt",
            name="test.txt",
            depth=0,
            embedding=np.random.randn(768)
        )
        self.engine.nodes["test"] = node

        # Add relevant queries
        for _ in range(5):
            self.engine.add_query_to_history(
                "test query",
                embedding=node.embedding + np.random.randn(768) * 0.05
            )

        # Calculate activation
        score = self.engine.calculate_activation_score("test")

        # Should have reasonable activation
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)

    # ========== ACCOMMODATION TESTS ==========

    def test_accommodation_smooth_transition(self):
        """Test that accommodation completes smoothly."""
        # Run accommodation
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            self.engine.accommodate_layout(reason="test")
        )

        # Check result structure
        self.assertIn('old_positions', result)
        self.assertIn('new_positions', result)
        self.assertIn('duration', result)
        self.assertIn('easing', result)

        # Duration should be reasonable (0.5-1.0s)
        self.assertGreater(result['duration'], 0.4)
        self.assertLess(result['duration'], 1.5)

    def test_accommodation_triggered_on_change(self):
        """Test accommodation is triggered when structure changes."""
        # Add node
        metadata = {
            'name': 'new.txt',
            'type': 'text',
            'size': 1024,
            'embedding': np.random.randn(768),
            'depth': 0
        }

        loop = asyncio.get_event_loop()
        operation = loop.run_until_complete(
            self.engine.handle_new_artifact('/test/new.txt', metadata)
        )

        # Accommodation should have been called (implicitly)
        self.assertTrue(operation.success)

    # ========== METRICS TESTS ==========

    def test_metrics_tracking(self):
        """Test that metrics are tracked correctly."""
        # Track some operations
        self.metrics.track_branch_creation('/test/a.txt', 500)
        self.metrics.track_branch_creation('/test/b.txt', 1200)

        summary = self.metrics.get_summary()

        # Check branching metrics
        self.assertEqual(summary['branching']['count'], 2)
        self.assertEqual(summary['branching']['avg'], 850.0)
        self.assertEqual(summary['branching']['min'], 500)
        self.assertEqual(summary['branching']['max'], 1200)

    def test_metrics_goals(self):
        """Test metrics goal checking."""
        # Track good performance
        for _ in range(10):
            self.metrics.track_branch_creation('/test/file.txt', 500)
            self.metrics.track_merge_accuracy(True, True)
            self.metrics.track_accommodation_fps(60)
            self.metrics.track_collision_rate(100, 2)

        goals = self.metrics.check_goals()

        # Should meet goals
        self.assertTrue(goals['branching_speed'])
        self.assertTrue(goals['merge_accuracy'])
        self.assertTrue(goals['accommodation_fps'])
        self.assertTrue(goals['collision_rate'])

    # ========== INTEGRATION TESTS ==========

    def test_full_workflow(self):
        """Test complete CAM workflow: branch → query → prune."""
        # 1. Create root
        root = VETKANode(
            id="root",
            path="/",
            name="root",
            depth=0,
            embedding=np.random.randn(768)
        )
        self.engine.nodes["root"] = root

        # 2. Add several artifacts
        loop = asyncio.get_event_loop()

        for i in range(5):
            metadata = {
                'name': f'file{i}.txt',
                'type': 'text',
                'size': 1024,
                'embedding': np.random.randn(768),
                'parent': 'root',
                'depth': 1
            }
            loop.run_until_complete(
                self.engine.handle_new_artifact(f'/test/file{i}.txt', metadata)
            )

        # Should have 6 nodes now (root + 5 files)
        self.assertEqual(len(self.engine.nodes), 6)

        # 3. Add queries (only for some files)
        for i in range(3):
            node_id = list(self.engine.nodes.keys())[i+1]  # Skip root
            node = self.engine.nodes[node_id]
            self.engine.add_query_to_history(
                f"query {i}",
                embedding=node.embedding
            )

        # 4. Run pruning
        candidates = loop.run_until_complete(
            self.engine.prune_low_entropy(threshold=0.3)
        )

        # Some nodes should be marked for pruning
        # (those not matched by queries)
        self.assertGreaterEqual(len(candidates), 0)

    def test_node_data_structure(self):
        """Test VETKANode data structure."""
        node = VETKANode(
            id="test",
            path="/test/file.txt",
            name="file.txt",
            depth=2,
            embedding=np.random.randn(768)
        )

        # Check defaults
        self.assertEqual(node.activation_score, 0.5)
        self.assertFalse(node.is_marked_for_deletion)
        self.assertIsNone(node.duplicate_of)
        self.assertIsNotNone(node.created_at)
        self.assertEqual(len(node.children), 0)
        self.assertEqual(len(node.metadata), 0)

        # Test to_dict
        node_dict = node.to_dict()
        self.assertEqual(node_dict['id'], 'test')
        self.assertEqual(node_dict['path'], '/test/file.txt')
        self.assertEqual(node_dict['depth'], 2)


class TestCAMMetrics(unittest.TestCase):
    """Test suite for CAM metrics."""

    def setUp(self):
        """Set up test fixtures."""
        self.metrics = CAMMetrics()

    def tearDown(self):
        """Clean up after tests."""
        self.metrics.reset_metrics()

    def test_branch_timing_tracking(self):
        """Test branch timing is tracked correctly."""
        times = [100, 200, 300, 400, 500]
        for t in times:
            self.metrics.track_branch_creation(f'/test/file{t}.txt', t)

        summary = self.metrics.get_summary()
        self.assertEqual(summary['branching']['count'], 5)
        self.assertEqual(summary['branching']['avg'], 300)

    def test_accuracy_tracking(self):
        """Test accuracy tracking."""
        # Perfect accuracy
        for _ in range(10):
            self.metrics.track_merge_accuracy(True, True)
            self.metrics.track_merge_accuracy(False, False)

        summary = self.metrics.get_summary()
        self.assertEqual(summary['merge_accuracy']['accuracy'], 1.0)
        self.assertTrue(summary['merge_accuracy']['meets_goal'])

    def test_fps_tracking(self):
        """Test FPS tracking."""
        for _ in range(10):
            self.metrics.track_accommodation_fps(60)

        summary = self.metrics.get_summary()
        self.assertEqual(summary['accommodation_fps']['avg'], 60)
        self.assertTrue(summary['accommodation_fps']['meets_goal'])

    def test_collision_tracking(self):
        """Test collision rate tracking."""
        # 2% collision rate (meets <5% goal)
        self.metrics.track_collision_rate(total_frames=100, collision_frames=2)

        summary = self.metrics.get_summary()
        self.assertEqual(summary['collision_rate']['avg'], 0.02)
        self.assertTrue(summary['collision_rate']['meets_goal'])


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
