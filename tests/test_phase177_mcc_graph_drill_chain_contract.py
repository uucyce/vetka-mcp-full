from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCC = ROOT / 'client/src/components/mcc/MyceliumCommandCenter.tsx'


def test_mcc_uses_chain_state_for_roadmap_drill():
    text = MCC.read_text()
    assert "const [roadmapDrillNodeChain, setRoadmapDrillNodeChain] = useState<string[]>([]);" in text
    assert "const roadmapDrillNodeId = roadmapDrillNodeChain.length > 0 ? roadmapDrillNodeChain[roadmapDrillNodeChain.length - 1] : null;" in text
    assert "for (let idx = 0; idx < roadmapDrillNodeChain.length; idx += 1) {" in text
    assert "const nextAnchorId = roadmapDrillNodeChain[idx + 1] || '';" in text


def test_mcc_resolves_rd_nodes_back_to_anchor_ids():
    text = MCC.read_text()
    assert "function resolveRoadmapDrillAnchorId(nodes: DAGNode[], nodeId: string): string {" in text
    assert "return String(meta.rd_origin_id || nodeId || '');" in text
    assert "rd_origin_id: childId," in text


def test_mcc_truncates_chain_only_when_ancestor_is_clicked():
    text = MCC.read_text()
    assert "const existingIndex = roadmapDrillNodeChain.indexOf(anchorId);" in text
    assert "const hasDescendantsExpanded = existingIndex >= 0 && existingIndex < roadmapDrillNodeChain.length - 1;" in text
    assert "return prev.slice(0, idx + 1);" in text
    assert "return prev.length === 1 ? [] : prev;" in text
