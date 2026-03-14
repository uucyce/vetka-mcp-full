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


def test_mcc_switches_branch_when_new_top_level_anchor_is_clicked():
    text = MCC.read_text()
    assert "const isInlineRoadmapDescendant = Boolean(" in text
    assert "nodeId.startsWith('rd_')" in text
    assert "if (!isInlineRoadmapDescendant) {" in text
    assert "return [anchorId];" in text


def test_mcc_roadmap_drill_materializes_one_generation_per_expand():
    text = MCC.read_text()
    assert "MARKER_177.MCC.INFINITE_DRILL.ONE_LEVEL" in text
    assert "depth1.forEach((id) => pushNode(id, 1));" in text
    assert "depth2.forEach((id) => pushNode(id, 2));" not in text
    assert "pushOverflowNode(2, depth2Overflow);" not in text


def test_mcc_roadmap_drill_uses_directed_children_not_undirected_neighbors():
    text = MCC.read_text()
    assert "const childrenByParent = new Map<string, Set<string>>();" in text
    assert "connectChild(String(e.source || ''), String(e.target || ''));" in text
    assert "connect(e.target, e.source);" not in text
    assert "Array.from(childrenByParent.get(parentAnchorId) || [])" in text
