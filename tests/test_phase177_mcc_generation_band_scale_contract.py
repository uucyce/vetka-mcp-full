from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE = ROOT / 'client/src/components/mcc/nodes/RoadmapTaskNode.tsx'
DAG = ROOT / 'client/src/components/mcc/DAGView.tsx'
DOC = ROOT / 'docs/177_MCC_local/MARKER_177_MCC_GENERATION_BAND_RECON.md'


def test_generation_band_policy_splits_depth_1_2_and_3_plus():
    text = NODE.read_text()
    assert 'if (depth <= 1) {' in text
    assert 'if (depth === 2) {' in text
    assert 'visualFloor: 0.08,' in text
    assert 'visualFloor: 0.04,' in text
    assert 'visualFloor: 0.02,' in text
    assert 'labelFontFloor: 3,' in text
    assert 'labelFontFloor: 2,' in text
    assert 'labelFontFloor: 1,' in text


def test_generation_band_spacing_scales_with_cumulative_depth():
    text = DAG.read_text()
    assert 'let accumulatedYOffset = 0;' in text
    assert 'const rowDepthTotal = Math.max(1, Number((row[0]?.data as any)?.rd_depth_total || d));' in text
    assert 'const generationBand = rowDepthTotal <= 1 ? 1 : rowDepthTotal === 2 ? 2 : 3;' in text
    assert 'const baseYOffset = generationBand === 1' in text
    assert 'const xGap = generationBand === 1' in text
    assert 'const yGap = generationBand === 1' in text
    assert 'accumulatedYOffset += baseYOffset;' in text
    assert 'accumulatedYOffset += yGap;' in text


def test_generation_band_recon_doc_tracks_playwright_gap():
    text = DOC.read_text()
    assert 'MARKER_177.GEN_BAND.PLAYWRIGHT_PATH' in text
    assert 'hydrated project context' in text
    assert 'generation-aware policy split' in text
