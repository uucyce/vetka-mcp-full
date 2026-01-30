"""
Token estimation utilities.

@status: active
@phase: 97
@depends: None
@used_by: src.api.handlers.message_utils, src.orchestration.context_fusion
"""


def estimate_tokens(text: str) -> int:
    """
    Estimate token count (rough approximation: ~4 chars per token).

    This is a simple heuristic that works reasonably well for most text.
    For more accurate counts, use tiktoken or the model's tokenizer.

    Args:
        text: Input text to estimate tokens for

    Returns:
        Estimated token count
    """
    if not text:
        return 0
    return len(text) // 4


# Alias for backwards compatibility
_estimate_tokens = estimate_tokens
