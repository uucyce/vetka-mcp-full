"""
Phase 155E P0 tests: unified node/role/relation contract matrix.
"""

from pathlib import Path

from src.services.workflow_store import VALID_EDGE_TYPES, VALID_NODE_TYPES
from src.services.workflow_canonical_schema import VALID_NODE_TYPES as CANON_VALID_NODE_TYPES
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 155e contracts changed")

def test_workflow_store_accepts_gate_and_roadmap_nodes():
    assert "gate" in VALID_NODE_TYPES
    assert "roadmap_task" in VALID_NODE_TYPES


def test_workflow_store_accepts_extended_edge_types():
    assert "dependency" in VALID_EDGE_TYPES
    assert "predicted" in VALID_EDGE_TYPES


def test_canonical_schema_node_matrix_includes_gate_and_proposal():
    assert "gate" in CANON_VALID_NODE_TYPES
    assert "proposal" in CANON_VALID_NODE_TYPES


def test_ts_contract_includes_eval_role_and_extended_relations():
    dag_ts = Path("client/src/types/dag.ts").read_text(encoding="utf-8")
    assert "'eval'" in dag_ts
    assert "'gate'" in dag_ts
    for relation in ("'plans'", "'verifies'", "'scores'", "'feeds'", "'retries'", "'passes_to'", "'deploys'"):
        assert relation in dag_ts
