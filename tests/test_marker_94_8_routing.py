#!/usr/bin/env python3
"""
Test for MARKER_94.8: Provider routing bug fix

This test verifies that the detect_provider function correctly routes:
1. x-ai/grok-4 -> OPENROUTER (not XAI)
2. grok-4 -> XAI (direct API)
3. Other models -> correct providers
"""

from src.elisya.provider_registry import ProviderRegistry, Provider


def test_detect_provider():
    """Test the detect_provider routing logic."""

    test_cases = [
        # (model_name, expected_provider, description)
        ("x-ai/grok-4", Provider.OPENROUTER, "OpenRouter xAI model with x-ai/ prefix"),
        ("x-ai/grok-beta", Provider.OPENROUTER, "OpenRouter xAI beta model"),
        ("xai/grok-4", Provider.OPENROUTER, "OpenRouter xAI model with xai/ prefix"),
        ("grok-4", Provider.XAI, "Direct xAI API model"),
        ("grok-beta", Provider.XAI, "Direct xAI API beta model"),
        ("grok", Provider.XAI, "Direct xAI API base model"),
        ("gpt-4", Provider.OPENAI, "OpenAI direct (matches gpt- pattern)"),
        ("openai/gpt-4", Provider.OPENAI, "OpenAI via OpenRouter"),
        ("claude-3", Provider.ANTHROPIC, "Anthropic direct (matches claude- pattern)"),
        ("anthropic/claude-3", Provider.ANTHROPIC, "Anthropic via OpenRouter"),
        ("qwen2:7b", Provider.OLLAMA, "Ollama local model (has colon)"),
        ("gemini-pro", Provider.GOOGLE, "Google Gemini direct"),
        ("google/gemini-2", Provider.GOOGLE, "Google via OpenRouter"),
        ("unknown/model-123", Provider.OPENROUTER, "Unknown provider with slash -> OpenRouter"),
    ]

    passed = 0
    failed = 0

    print("\n" + "="*80)
    print("MARKER_94.8 ROUTING FIX TEST")
    print("="*80 + "\n")

    for model_name, expected, description in test_cases:
        result = ProviderRegistry.detect_provider(model_name)
        status = "✅ PASS" if result == expected else "❌ FAIL"

        if result == expected:
            passed += 1
        else:
            failed += 1

        print(f"{status} | {model_name:25} | Expected: {expected.value:12} | Got: {result.value:12}")
        print(f"       └─ {description}")
        print()

    print("="*80)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*80 + "\n")

    return failed == 0


if __name__ == "__main__":
    import sys
    success = test_detect_provider()
    sys.exit(0 if success else 1)
