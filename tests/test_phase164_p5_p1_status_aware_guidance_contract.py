from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding='utf-8')


def test_status_aware_guidance_markers_and_branches_present():
    chat = _read('client/src/components/mcc/MiniChat.tsx')
    mcc = _read('client/src/components/mcc/MyceliumCommandCenter.tsx')

    assert 'MARKER_164.P5.P1.MYCO.CHAT_STATUS_AWARE_NEXT_ACTIONS.V1' in chat
    assert 'MARKER_164.P5.P1.MYCO.TOP_HINT_STATUS_AWARE_WORKFLOW_ACTIONS.V1' in mcc

    for token in ('running', 'done', 'failed'):
      assert token in chat
      assert token in mcc

    assert 'monitor Stats/stream' in chat
    assert (
        'review artifacts and proceed' in mcc
        or 'review artifacts -> pick next queued/pending task in Tasks' in mcc
    )
    assert (
        'inspect failure and retry' in mcc
        or 'inspect failure in Context -> retry with corrected model/prompt' in mcc
    )
