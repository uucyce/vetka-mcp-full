from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MINI_CHAT = ROOT / 'client/src/components/mcc/MiniChat.tsx'


def test_minichat_uses_runtime_target_and_history_path():
    text = MINI_CHAT.read_text()
    assert 'function buildQuickChatNodePath' in text
    assert 'function useChatRuntimeTarget' in text
    assert 'selected_key_provider' in text
    assert 'model_source' in text
    assert '/chat/history?path=' in text
    assert 'setLastQuestion(message)' in text
    assert 'Backend model unavailable' not in text
