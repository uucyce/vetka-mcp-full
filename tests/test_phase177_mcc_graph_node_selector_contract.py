from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE = ROOT / 'client/src/components/mcc/nodes/RoadmapTaskNode.tsx'


def test_mcc_roadmap_node_exposes_stable_playwright_selectors():
    text = NODE.read_text()
    assert 'data-testid="mcc-roadmap-node"' in text
    assert 'data-node-label={data.label}' in text
    assert 'data-graph-kind={graphKind || \"\"}' in text or "data-graph-kind={graphKind || ''}" in text
    assert "data-scope-kind={isProjectRoot ? 'root' : isProjectDir ? 'directory' : isDocumentScope ? 'document' : isCodeFileScope ? 'code' : 'task'}" in text
    assert 'data-rd-depth-total={String(fractalDepth)}' in text
    assert 'data-node-task-id={data.taskId || \"\"}' in text or "data-node-task-id={data.taskId || ''}" in text
