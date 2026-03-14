from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCC = ROOT / 'client/src/components/mcc/MyceliumCommandCenter.tsx'
DAG = ROOT / 'client/src/components/mcc/DAGView.tsx'
NODE = ROOT / 'client/src/components/mcc/nodes/RoadmapTaskNode.tsx'


def test_mcc_writes_cumulative_rd_depth_total_for_overlay_nodes_and_edges():
    text = MCC.read_text()
    assert 'const parentFractalDepth = Math.max(' in text
    assert 'rd_depth_total: parentFractalDepth + depth,' in text
    assert 'data: {' in text
    assert 'rd_depth_total: parentFractalDepth + depth,' in text


def test_dag_edges_scale_by_fractal_depth_total():
    text = DAG.read_text()
    assert "const fractalDepth = Math.max(0, Number((edge.data as any)?.rd_depth_total || 0));" in text
    assert "const fractalEdgeScale = Math.max(0.38, 1 / Math.pow(1.6, fractalDepth));" in text
    assert 'strokeWidth: isMicroInline ? Math.max(0.34, 0.7 * fractalEdgeScale)' in text
    assert 'opacity: isMicroInline ? Math.max(0.42, 0.78 * fractalEdgeScale)' in text


def test_roadmap_node_scales_handles_and_border_with_visual_scale():
    text = NODE.read_text()
    assert 'type MiniGenerationPolicy = {' in text
    assert 'function getMiniGenerationPolicy(depth: number): MiniGenerationPolicy {' in text
    assert "const generationPolicy = getMiniGenerationPolicy(fractalDepth);" in text
    assert "const visualScale = isMini ? Math.max(generationPolicy.visualFloor, compactScale * fractalScale) : fractalScale;" in text
    assert "const edgeScale = Math.max(generationPolicy.edgeFloor, visualScale);" in text
    assert "border: `${scalePx(2, edgeScale, 1)}px solid ${semanticBorderColor}`" in text
    assert "minWidth: isMini ? scalePx(160, visualScale, generationPolicy.minWidthFloor) : scalePx(isCodeScope ? 180 : 160, visualScale, 120)" in text
    assert "maxWidth: isMini ? scalePx(200, visualScale, generationPolicy.maxWidthFloor) : scalePx(isCodeScope ? 220 : 200, visualScale, 140)" in text
    assert "width: isMini ? scalePx(8, edgeScale, generationPolicy.handleFloor) : scalePx(8, edgeScale, 4)" in text
    assert "height: isMini ? scalePx(8, edgeScale, generationPolicy.handleFloor) : scalePx(8, edgeScale, 4)" in text
    assert "fontSize: isMini ? scalePx(11, visualScale, generationPolicy.labelFontFloor) : scalePx(isCodeScope ? 12 : 11, visualScale, 9)" in text
