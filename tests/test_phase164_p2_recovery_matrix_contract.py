from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding='utf-8')


def test_recovery_matrix_doc_exists_and_has_marker():
    text = _read('docs/164_MYCO_ARH_MCC/PHASE_164_P2_RECOVERY_BRANCHES_MATRIX_2026-03-08.md')
    assert 'MARKER_164.P2.RECOVERY_BRANCHES_MATRIX.V1' in text


def test_recovery_matrix_contains_required_branches():
    text = _read('docs/164_MYCO_ARH_MCC/PHASE_164_P2_RECOVERY_BRANCHES_MATRIX_2026-03-08.md')
    for token in ['R1', 'R2', 'R3', 'R4', 'R5', 'R6']:
        assert token in text
    assert 'context mismatch' in text
