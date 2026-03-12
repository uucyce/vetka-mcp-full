from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROADMAP_NODE = ROOT / 'client/src/components/mcc/nodes/RoadmapTaskNode.tsx'
MINI_CONTEXT = ROOT / 'client/src/components/mcc/MiniContext.tsx'
DAG_LAYOUT = ROOT / 'client/src/utils/dagLayout.ts'


def test_code_scope_nodes_have_distinct_projection_and_fractal_scale():
    text = ROADMAP_NODE.read_text()
    assert "const fractalDepth = Math.max(0, Number(data.rd_depth_total ?? data.rd_depth ?? 0));" in text
    assert "const fractalScale = Math.max(0.34, 1 / Math.pow(1.6, fractalDepth));" in text
    assert "const edgeScale = Math.max(0.08, visualScale);" in text
    assert "const isCodeScope = graphKind === 'project_dir' || graphKind === 'project_file' || graphKind === 'project_root';" in text
    assert "const codeKindLabel = graphKind === 'project_dir' ? 'DIR' : graphKind === 'project_file' ? 'FILE' : graphKind === 'project_root' ? 'ROOT' : '';" in text
    assert "{isCodeScope && codeKindLabel ? (" in text
    assert "code scope" in text
    assert "inside ${data.description}" in text


def test_code_scope_context_gets_breadcrumb_header():
    text = MINI_CONTEXT.read_text()
    assert 'function CodeBreadcrumbs' in text
    assert 'code scope switch:' in text
    assert "<Section title={(context.nodeKind === 'file' || context.nodeKind === 'directory') ? 'Code Summary' : 'Summary'}>" in text


def test_graph_layout_passes_graph_kind_into_node_data():
    text = DAG_LAYOUT.read_text()
    assert 'graphKind: node.graphKind' in text
    assert "rd_depth_total: Number((node as any)?.metadata?.rd_depth_total || (node as any)?.metadata?.rd_depth || 0)," in text
