from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAG_LAYOUT = ROOT / 'client/src/utils/dagLayout.ts'
TASK_DAG = ROOT / 'client/src/components/mcc/TaskDAGView.tsx'
ARCH = ROOT / 'docs/177_MCC_local/MCC_CODE_CONTEXT_INSPECTION_ARCHITECTURE.md'


def test_struct_labels_hidden_in_normal_mode():
    dag = DAG_LAYOUT.read_text()
    task = TASK_DAG.read_text()
    assert "return { label: '', color: NOLAN_PALETTE.textDim };" in dag
    assert "return { label: '', color: NOLAN_PALETTE.textDim };" in task
    assert "label: 'struct'" not in dag
    assert "label: 'struct'" not in task


def test_fractal_scale_doc_pins_phi_step():
    text = ARCH.read_text()
    assert '1 / 1.6' in text
    assert '1 / 1.6^2' in text
    assert '1 / 1.6^3' in text
    assert '1.618' in text
