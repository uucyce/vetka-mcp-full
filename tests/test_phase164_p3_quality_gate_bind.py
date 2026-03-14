from pathlib import Path
from src.api.routes.chat_routes import (
    _build_role_aware_instruction_packet,
    _build_architect_quick_system_prompt,
)


def _read(path: str) -> str:
    return Path(path).read_text(encoding='utf-8')


def test_quality_gate_doc_has_marker_and_test_package_refs():
    text = _read('docs/164_MYCO_ARH_MCC/PHASE_164_P3_QUALITY_GATE_BIND_2026-03-08.md')
    assert 'MARKER_164.P3.QUALITY_GATE_AUTOTEST_BIND.V1' in text
    assert 'test_phase164_p2_trigger_matrix_contract.py' in text


def test_quality_gate_code_bind_role_core_and_prompt():
    packet = _build_role_aware_instruction_packet('architect', {
        'nav_level': 'roadmap',
        'node_kind': 'task',
        'task_id': 'tb_9',
    })
    assert packet['architect_scope'] == 'task_architect'
    assert len(packet['next_actions']) == 3
    prompt = _build_architect_quick_system_prompt({'chat_scope': 'project'})
    assert 'project architect' in prompt
    assert 'tools:' in prompt
