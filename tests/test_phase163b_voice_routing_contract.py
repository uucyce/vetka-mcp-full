import importlib
import sys
from types import ModuleType
from pathlib import Path


def _load_jarvis_handler():
    fake_tts_engine = ModuleType("src.voice.tts_engine")
    fake_tts_engine.Qwen3TTSClient = object
    fake_tts_engine.FastTTSClient = object
    fake_tts_engine.ESpeakTTSClient = object
    sys.modules["src.voice.tts_engine"] = fake_tts_engine

    fake_whisper = ModuleType("mlx_whisper")
    fake_whisper.transcribe = lambda *args, **kwargs: {"text": "", "segments": []}
    sys.modules["mlx_whisper"] = fake_whisper
    return importlib.import_module("src.api.handlers.jarvis_handler")


def test_voice_runtime_routes_myco_to_espeak_chip():
    jh = _load_jarvis_handler()
    runtime = jh._resolve_voice_runtime_for_context({"agent_role": "myco"}, "ru")
    assert runtime["agent_role"] == "myco"
    assert runtime["provider"] == "espeak"
    assert runtime["voice_profile"] == "myco_chip_ru"
    assert runtime["espeak_preset"] == "chip"


def test_voice_runtime_routes_vetka_to_edge_female():
    jh = _load_jarvis_handler()
    runtime = jh._resolve_voice_runtime_for_context({"agent_role": "vetka"}, "ru")
    assert runtime["agent_role"] == "vetka"
    assert runtime["provider"] == "edge"
    assert runtime["voice_profile"] == "vetka_ru_female"


def test_extract_client_context_whitelists_supported_agent_role_only():
    jh = _load_jarvis_handler()
    ctx = jh._extract_client_context({"agent_role": "vetka", "llm_model": "foo"})
    assert ctx["agent_role"] == "vetka"
    ctx2 = jh._extract_client_context({"agent_role": "unknown"})
    assert "agent_role" not in ctx2


def test_myco_deterministic_speech_can_auto_resume_listening_contract():
    hook = (Path(__file__).resolve().parents[1] / "client/src/hooks/useJarvis.ts").read_text(encoding="utf-8")
    assert "autoListenAfter?: boolean" in hook
    assert "conversationActiveRef.current = Boolean(options?.autoListenAfter);" in hook
