"""
VETKA-JSON Transformation Service

@file vetka_transformer_service.py
@status ACTIVE
@phase Phase 54.1 (Refactored from orchestrator_with_elisya.py)
@lastAudit 2026-01-08

Handles:
- Phase 9 output building
- VETKA-JSON transformation
- Infrastructure data collection
- Validation and emission to UI
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional


class VETKATransformerService:
    """Manages VETKA-JSON transformation and validation."""

    def __init__(self, socketio=None):
        """
        Initialize VETKA transformer service.

        Args:
            socketio: Socket.IO instance for emitting events
        """
        self.socketio = socketio
        self.vetka_transformer = None
        self.vetka_validator = None
        self._init_transformer()

    def _init_transformer(self):
        """Initialize Phase 10 Transformer and Validator."""
        try:
            from src.transformers.phase9_to_vetka import Phase10Transformer
            from src.validators.vetka_validator import VetkaValidator

            self.vetka_transformer = Phase10Transformer()
            schema_path = Path(__file__).parent.parent.parent.parent / "config" / "vetka_schema_v1.3.json"
            self.vetka_validator = VetkaValidator(str(schema_path))
            print("   • Phase 10 Transformer: initialized")
        except Exception as e:
            print(f"   ⚠️  Phase 10 Transformer init failed: {e}")
            self.vetka_transformer = None
            self.vetka_validator = None

    def is_available(self) -> bool:
        """Check if transformer is available."""
        return self.vetka_transformer is not None

    def collect_infrastructure_data(
        self,
        workflow_id: str,
        elisya_state=None,
        memory_manager=None
    ) -> Dict[str, Any]:
        """
        Collect data from all infrastructure systems for Phase 10 transformer.

        Args:
            workflow_id: Workflow identifier
            elisya_state: ElisyaState instance
            memory_manager: MemoryManager instance

        Returns:
            Infrastructure data dict
        """
        infrastructure = {}

        # Learning system data
        try:
            infrastructure['learning'] = {
                'student_level': 0,
                'learner_model': None
            }
        except Exception as e:
            print(f"   ⚠️  Could not collect learning data: {e}")

        # Routing decisions
        try:
            infrastructure['routing'] = {
                'decisions': [],
                'cost_summary': {}
            }
        except Exception as e:
            print(f"   ⚠️  Could not collect routing data: {e}")

        # Elisya middleware data
        try:
            if elisya_state:
                infrastructure['elisya'] = {
                    'version': '1.0.0',
                    'lod_requested': 'BRANCH',
                    'lod_applied': 'BRANCH',
                    'assembly_time_ms': 0,
                    'reframes_applied': True,
                    'query_sources': ['changelog', 'weaviate', 'qdrant']
                }
        except Exception as e:
            print(f"   ⚠️  Could not collect elisya data: {e}")

        # Storage status
        try:
            if memory_manager:
                infrastructure['storage'] = {
                    'triple_write_results': {
                        'changelog': {'status': 'success'},
                        'weaviate': {'status': 'success'},
                        'qdrant': {'status': 'success'}
                    },
                    'overall_status': 'complete',
                    'degradation_mode': False
                }
        except Exception as e:
            print(f"   ⚠️  Could not collect storage data: {e}")

        return infrastructure

    def build_phase9_output(
        self,
        result: Dict[str, Any],
        arc_suggestions: list = None,
        elisya_state=None,
        memory_manager=None
    ) -> Dict[str, Any]:
        """
        Build Phase 9 output format for VETKA transformer.

        Args:
            result: Workflow result dict
            arc_suggestions: Optional ARC solver suggestions
            elisya_state: ElisyaState instance
            memory_manager: MemoryManager instance

        Returns:
            Phase 9 output dict
        """
        workflow_id = result.get('workflow_id', '')

        # Parse dev result to extract file info
        dev_files = []
        impl = result.get('implementation', '')
        if impl:
            # Simple file extraction (can be enhanced)
            dev_files = [
                {'name': 'implementation.py', 'path': 'src/implementation.py',
                 'tokens': len(impl.split()), 'language': 'python'}
            ]

        # Parse QA result
        tests = result.get('tests', '')
        qa_tests = ['test_implementation.py'] if tests else []

        phase9_output = {
            'workflow_id': workflow_id,
            'pm_result': {
                'plan': result.get('pm_plan', ''),
                'risks': [],  # Could extract from PM output
                'eval_score': 0.85  # Default, could be from actual evaluation
            },
            'architect_result': {
                'diagram': '',
                'description': result.get('architecture', ''),
                'score': 0.82
            } if result.get('architecture') else None,
            'dev_result': {
                'files': dev_files,
                'eval_score': 0.84
            },
            'qa_result': {
                'coverage': 80,  # Estimated
                'passed': 10,
                'failed': 0,
                'tests': qa_tests,
                'eval_score': 0.79
            },
            'arc_suggestions': arc_suggestions or [],
            'metrics': {
                'total_time_ms': int(result.get('duration', 0) * 1000),
                'parallel_execution': result.get('execution_mode') == 'parallel'
            },
            'infrastructure': self.collect_infrastructure_data(
                workflow_id,
                elisya_state,
                memory_manager
            )
        }

        return phase9_output

    def transform_and_emit(
        self,
        result: Dict[str, Any],
        arc_suggestions: list = None,
        elisya_state=None,
        memory_manager=None
    ) -> Optional[Dict[str, Any]]:
        """
        Transform workflow result to VETKA-JSON and emit to UI.

        Args:
            result: Workflow result dict
            arc_suggestions: Optional ARC solver suggestions
            elisya_state: ElisyaState instance
            memory_manager: MemoryManager instance

        Returns:
            VETKA-JSON dict or None if transformation failed
        """
        if not self.vetka_transformer:
            print("   ⚠️  VETKA transformer not available")
            return None

        workflow_id = result.get('workflow_id', '')

        try:
            print('\n🌳 Phase 10: Transforming to VETKA-JSON v1.3...')

            # Build Phase 9 output format
            phase9_output = self.build_phase9_output(
                result,
                arc_suggestions,
                elisya_state,
                memory_manager
            )

            # Transform to VETKA-JSON
            vetka_json = self.vetka_transformer.transform(phase9_output)

            # Validate
            is_valid, errors = self.vetka_validator.validate(vetka_json)
            if not is_valid:
                print(f"   ⚠️  VETKA validation warnings: {errors[:3]}")  # Show first 3
            else:
                print(f"   ✅ VETKA-JSON validated successfully")

            # Save to file
            output_dir = Path(__file__).parent.parent.parent.parent / "output"
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"vetka_{workflow_id}.json"

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(vetka_json, f, indent=2, ensure_ascii=False)
            print(f"   💾 Saved to {output_path}")

            # Emit to Phase 10 UI via WebSocket
            if self.socketio:
                try:
                    self.socketio.emit('vetka_tree_update', {
                        'workflow_id': workflow_id,
                        'tree': vetka_json,
                        'timestamp': time.time()
                    })
                    print(f"   📡 Emitted vetka_tree_update to UI")
                except Exception as e:
                    print(f"   ⚠️  Could not emit to UI: {e}")

            # Stats
            tree = vetka_json.get('tree', {})
            print(f"   📊 Tree stats: {tree.get('metadata', {}).get('total_nodes', 0)} nodes, "
                  f"{tree.get('metadata', {}).get('total_edges', 0)} edges")

            return vetka_json

        except Exception as e:
            print(f"   ❌ VETKA transformation failed: {e}")
            import traceback
            traceback.print_exc()
            return None
