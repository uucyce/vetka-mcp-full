from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCC = ROOT / 'client/src/components/mcc/MyceliumCommandCenter.tsx'
DOC = ROOT / 'docs/177_MCC_local/MCC_CODE_CONTEXT_INSPECTION_ARCHITECTURE.md'


def test_mcc_suppresses_canonical_duplicates_when_inline_descendants_exist():
    text = MCC.read_text()
    assert 'const inlineOriginIds = new Set<string>(' in text
    assert ".map((n: DAGNode) => String((n.metadata as any)?.rd_origin_id || ''))" in text
    assert "const branchRootId = String(roadmapDrillNodeChain[0] || '');" in text
    assert "if (String(n.id).startsWith('rd_')) return true;" in text
    assert "if (!inlineOriginIds.has(String(n.id))) return true;" in text
    assert "return branchRootId !== '' && String(n.id) === branchRootId;" in text
    assert 'const filteredEdges = roadmapNodeExpanded.edges.filter(' in text


def test_architecture_doc_records_projection_echo_suppression_rule():
    text = DOC.read_text()
    assert 'duplicate canonical node' in text
    assert 'rd_origin_id' in text
