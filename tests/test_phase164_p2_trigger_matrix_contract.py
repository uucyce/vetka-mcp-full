from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding='utf-8')


def test_trigger_matrix_doc_exists_and_has_marker():
    text = _read('docs/164_MYCO_ARH_MCC/PHASE_164_P2_TRIGGER_MATRIX_2026-03-08.md')
    assert 'MARKER_164.P2.FULL_TRIGGER_MATRIX_FROM_UI_ATLAS.V1' in text


def test_trigger_matrix_has_core_triggers():
    text = _read('docs/164_MYCO_ARH_MCC/PHASE_164_P2_TRIGGER_MATRIX_2026-03-08.md')
    for token in ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12', 'T13']:
        assert token in text
    assert '_normalize_guidance_context' in text
    assert '_build_role_aware_instruction_packet' in text
