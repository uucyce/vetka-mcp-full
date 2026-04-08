"""
CAM (Context-Aware Maintenance) Integration Service

@file cam_integration.py
@status ACTIVE
@phase Phase 54.1 (Refactored from orchestrator_with_elisya.py)
@lastAudit 2026-01-08

Handles:
- CAM Engine operations
- Low-entropy node pruning
- Subtree merging
- Artifact processing
"""

from typing import Dict, Any, Optional


class CAMIntegration:
    """Manages CAM Engine integration."""

    def __init__(self, memory_manager=None):
        """
        Initialize CAM integration.

        Args:
            memory_manager: MemoryManager instance for CAM Engine
        """
        self._cam_engine = None
        self._init_cam_engine(memory_manager)

    def _init_cam_engine(self, memory_manager):
        """Initialize CAM Engine if available."""
        try:
            from src.orchestration.cam_engine import VETKACAMEngine
            self._cam_engine = VETKACAMEngine(memory_manager=memory_manager)
            print("   • CAM Engine: initialized")
        except Exception as e:
            print(f"   ⚠️ CAM Engine init failed: {e}")
            self._cam_engine = None

    def is_available(self) -> bool:
        """Check if CAM Engine is available."""
        return self._cam_engine is not None

    async def maintenance_cycle(self) -> Dict[str, Any]:
        """
        Background CAM maintenance: prune low-entropy, merge similar subtrees.
        Should be called periodically (e.g., after workflow completion).

        @status ACTIVE
        @phase Phase 51.2 - Enhanced with logging
        @lastAudit 2026-01-07

        Returns:
            dict with prune_count, merge_count
        """
        if not self._cam_engine:
            print("[CAM] ⚠️ CAM Engine not initialized, skipping maintenance")
            return {'prune_count': 0, 'merge_count': 0, 'error': 'CAM Engine not initialized'}

        result = {'prune_count': 0, 'merge_count': 0}

        try:
            # Phase 51.2: Enhanced logging
            print("[CAM] 🔍 Analyzing knowledge graph for maintenance...")

            # Prune low-entropy nodes
            prune_candidates = await self._cam_engine.prune_low_entropy(threshold=0.2)
            if prune_candidates:
                result['prune_count'] = len(prune_candidates)
                print(f"[CAM] 🌱 Pruned {len(prune_candidates)} low-entropy nodes (threshold: 0.2)")
            else:
                print("[CAM] ✓ No low-entropy nodes to prune")

            # Find merge candidates
            merge_pairs = await self._cam_engine.merge_similar_subtrees(threshold=0.92)
            if merge_pairs:
                result['merge_count'] = len(merge_pairs)
                print(f"[CAM] 🔗 Merged {len(merge_pairs)} similar subtrees (similarity: 0.92)")
            else:
                print("[CAM] ✓ No similar subtrees to merge")

        except Exception as e:
            print(f"[CAM] ⚠️ Maintenance error: {e}")
            result['error'] = str(e)

        return result

    async def handle_new_artifact(
        self,
        artifact_path: str,
        metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Process new artifact created by agents.

        Args:
            artifact_path: Path to the artifact file
            metadata: Artifact metadata (type, agent, workflow_id, etc.)

        Returns:
            CAM operation result or None if CAM not available
        """
        if not self._cam_engine:
            return None

        try:
            cam_result = await self._cam_engine.handle_new_artifact(
                artifact_path=artifact_path,
                metadata=metadata
            )
            if cam_result:
                print(f"      🌱 CAM: {cam_result.operation_type} for {artifact_path}")
            return cam_result
        except Exception as e:
            print(f"      ⚠️ CAM processing failed: {e}")
            return None

    async def emit_workflow_complete_event(
        self,
        workflow_id: str,
        artifacts: list
    ) -> Dict[str, Any]:
        """
        Emit workflow completion event for CAM processing.

        Args:
            workflow_id: Workflow identifier
            artifacts: List of artifacts created

        Returns:
            Event processing result
        """
        try:
            from src.orchestration.cam_event_handler import emit_workflow_complete_event

            print(f"[CAM] Emitting workflow_completed event for {workflow_id}")
            cam_result = await emit_workflow_complete_event(
                workflow_id=workflow_id,
                artifacts=artifacts
            )

            if cam_result.get('status') == 'error':
                print(f"[CAM] Event error (non-critical): {cam_result.get('error')}")
            elif cam_result.get('status') == 'completed':
                print(f"[CAM] Maintenance completed: {cam_result.get('pruned', 0)} pruned, {cam_result.get('merged', 0)} merged")

            return cam_result

        except Exception as e:
            print(f"[CAM] Event error (non-critical): {e}")
            return {'status': 'error', 'error': str(e)}
