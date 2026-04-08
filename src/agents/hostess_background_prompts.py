"""
Hostess Background Prompts - System prompts for invisible background tasks.

Provides prompt templates for Hostess agent background tasks.
Currently only AUTO-SUMMARY scenario is active (10 min after chat idle).

@file hostess_background_prompts.py
@status: active
@phase: 96
@depends: None (pure prompt templates)
@used_by: Currently standalone, designed for hostess_agent.py background tasks

NOTE: Other scenarios (context prep, routing, review) were REMOVED because:
- Context prep BEFORE API = blocks and slows down (bad!)
- Routing = already removed from main flow
- Review = makes computer sound like forest in hurricane

Future scenarios require:
- Elisya middleware integration (memory, language)
- Knowledge level implementation
- Careful testing to not break Gemma Embedding
"""

# =============================================================================
# SCENARIO 1: AUTO-SUMMARY (10 min after chat close)
# The ONLY active background task for now
# =============================================================================

HOSTESS_SUMMARY_PROMPT = """Summarize this chat conversation.

CHAT:
{chat_history}

Extract:
- TOPIC: main discussion topic (1-3 words)
- SUMMARY: what was discussed (2-3 sentences)
- DECISIONS: key decisions made (list)
- TODO: action items remaining (list)
- NEXT_STEP: what to do next (1 sentence)

Output JSON:
{
  "topic": "...",
  "summary": "...",
  "decisions": ["..."],
  "todo": ["..."],
  "next_step": "..."
}"""


# =============================================================================
# FUTURE: These need investigation before enabling
# =============================================================================

# TODO Phase 81+: Links - requires knowledge level
# TODO Phase 81+: Compress - who was doing memory compression before?
# TODO Phase 81+: Metadata - check if breaks Gemma Embedding


def get_hostess_prompt(scenario: str, **kwargs) -> str:
    """Get formatted prompt for scenario.

    Args:
        scenario: Currently only "summary" is supported
        **kwargs: Variables to format into prompt

    Returns:
        Formatted prompt string

    Example:
        prompt = get_hostess_prompt("summary", chat_history="User: hello...")
    """
    if scenario == "summary":
        return HOSTESS_SUMMARY_PROMPT.format(**kwargs)
    else:
        raise ValueError(f"Unknown scenario: {scenario}. Only 'summary' is supported now.")
