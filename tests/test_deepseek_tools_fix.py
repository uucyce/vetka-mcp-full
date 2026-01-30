"""
Phase 80.5: Test for Deepseek Tool Support Fix

This test verifies that models without tool support don't cause 400 errors.

Run with: pytest tests/test_deepseek_tools_fix.py -v
"""

import pytest
from src.elisya.provider_registry import OllamaProvider, ProviderConfig


class TestDeepseekToolsFix:
    """Test tool support detection for Ollama models"""

    def setup_method(self):
        """Setup test provider"""
        config = ProviderConfig(api_key=None, base_url="http://localhost:11434")
        self.provider = OllamaProvider(config)

    def test_deepseek_no_tools(self):
        """Deepseek-llm should NOT support tools"""
        assert not self.provider._model_supports_tools('deepseek-llm:7b')
        assert not self.provider._model_supports_tools('deepseek-llm')

    def test_qwen_has_tools(self):
        """Qwen2.5 SHOULD support tools"""
        assert self.provider._model_supports_tools('qwen2.5:14b')
        assert self.provider._model_supports_tools('qwen2:7b')

    def test_llama2_no_tools(self):
        """Llama2 should NOT support tools"""
        assert not self.provider._model_supports_tools('llama2:7b')
        assert not self.provider._model_supports_tools('llama2')

    def test_codellama_no_tools(self):
        """CodeLlama should NOT support tools"""
        assert not self.provider._model_supports_tools('codellama:7b')

    def test_phi_no_tools(self):
        """Phi models should NOT support tools"""
        assert not self.provider._model_supports_tools('phi:latest')
        assert not self.provider._model_supports_tools('phi-2:latest')

    def test_gemma_no_tools(self):
        """Gemma should NOT support tools"""
        assert not self.provider._model_supports_tools('gemma:7b')

    def test_mistral_no_tools(self):
        """Mistral base should NOT support tools"""
        assert not self.provider._model_supports_tools('mistral:7b')

    def test_llama3_has_tools(self):
        """Llama3 SHOULD support tools (newer)"""
        assert self.provider._model_supports_tools('llama3:8b')
        assert self.provider._model_supports_tools('llama3.1:8b')

    def test_models_without_tools_list(self):
        """Verify all blacklisted models are detected"""
        for model in self.provider.MODELS_WITHOUT_TOOLS:
            assert not self.provider._model_supports_tools(f"{model}:latest"), \
                f"{model} should not support tools"

    def test_case_insensitive(self):
        """Tool detection should be case insensitive"""
        assert not self.provider._model_supports_tools('DeepSeek-LLM:7b')
        assert not self.provider._model_supports_tools('LLAMA2:7B')


@pytest.mark.asyncio
async def test_call_without_tools():
    """Test that call() properly strips tools for unsupported models"""
    config = ProviderConfig(api_key=None, base_url="http://localhost:11434")
    provider = OllamaProvider(config)

    # Mock tools
    tools = [
        {
            'type': 'function',
            'function': {
                'name': 'camera_focus',
                'description': 'Move 3D camera',
                'parameters': {}
            }
        }
    ]

    # This should NOT throw error even with tools parameter
    # (requires Ollama running with deepseek-llm:7b installed)
    try:
        # Note: This will fail if Ollama not running, which is expected in CI
        messages = [{'role': 'user', 'content': 'Hello'}]
        response = await provider.call(
            messages=messages,
            model='deepseek-llm:7b',
            tools=tools
        )
        # If we get here, tools were properly stripped
        assert response is not None
    except Exception as e:
        # Should NOT be a tools error
        assert 'does not support tools' not in str(e), \
            "Tools should have been stripped before call"
        # Connection errors are OK (Ollama not running)
        assert 'Connection' in str(e) or 'refused' in str(e) or 'No connection' in str(e)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
