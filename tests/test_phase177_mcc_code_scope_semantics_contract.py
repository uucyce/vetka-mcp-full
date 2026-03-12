from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROADMAP_NODE = ROOT / 'client/src/components/mcc/nodes/RoadmapTaskNode.tsx'
MINI_CONTEXT = ROOT / 'client/src/components/mcc/MiniContext.tsx'


def test_code_scope_cards_do_not_render_task_like_pending_semantics():
    text = ROADMAP_NODE.read_text()
    assert "const semanticBorderColor = isCodeScope ? 'rgba(180,190,205,0.38)' : borderColor;" in text
    assert "borderStyle: isCodeScope ? 'solid' : (isSuggested ? 'dashed' : 'solid')" in text
    assert "opacity: isCodeScope ? 1 : (isSuggested ? 0.58 : 1)" in text
    assert "{isCodeScope ? 'code scope' : data.status}" in text
    assert "inside ${data.description}" in text


def test_breadcrumb_jump_uses_explicit_context_switch_language():
    text = MINI_CONTEXT.read_text()
    assert 'code scope switch:' in text
    assert 'switch context to ${partialPath}' in text
    assert "snippet: 'code scope jump'" in text
