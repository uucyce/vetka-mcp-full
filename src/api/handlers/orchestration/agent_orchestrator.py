"""
Agent Orchestration Module.

Handles agent chain execution (PM -> Dev -> QA) with context passing.
Extracted from user_message_handler.py (lines 1317-1505).

@status: active
@phase: 96
@depends: utils.chat_utils
@used_by: di_container
"""

import asyncio
from typing import List, Dict, Any, Optional
from src.utils.chat_utils import get_agent_model_name


class AgentOrchestrator:
    """
    Orchestrates agent chain execution with context passing.

    Responsibilities:
    - Execute agent chain loop (PM → Dev → QA)
    - Pass previous outputs between agents
    - Extract artifacts from Dev responses
    - Extract QA scores from QA responses
    - Build prompts with chain context
    """

    def __init__(
        self,
        sio,
        sid: str,
        build_full_prompt_func,
        build_pinned_context_func,
        stream_response_func,
        extract_artifacts_func,
        extract_qa_score_func,
        extract_qa_verdict_func,
        ROLE_PROMPTS_AVAILABLE: bool,
        HOST_HAS_OLLAMA: bool,
    ):
        """
        Initialize orchestrator with dependencies.

        Args:
            sio: SocketIO server instance
            sid: Session ID
            build_full_prompt_func: Function to build prompts with chain context
            build_pinned_context_func: Function to build pinned files context
            stream_response_func: Function to stream responses
            extract_artifacts_func: Function to extract artifacts from Dev
            extract_qa_score_func: Function to extract QA score
            extract_qa_verdict_func: Function to extract QA verdict
            ROLE_PROMPTS_AVAILABLE: Whether role prompts are available
            HOST_HAS_OLLAMA: Whether Ollama is available on host
        """
        self.sio = sio
        self.sid = sid
        self.build_full_prompt = build_full_prompt_func
        self.build_pinned_context = build_pinned_context_func
        self.stream_response = stream_response_func
        self.extract_artifacts = extract_artifacts_func
        self.extract_qa_score = extract_qa_score_func
        self.extract_qa_verdict = extract_qa_verdict_func
        self.ROLE_PROMPTS_AVAILABLE = ROLE_PROMPTS_AVAILABLE
        self.HOST_HAS_OLLAMA = HOST_HAS_OLLAMA

    async def execute_agent_chain(
        self,
        agents_to_call: List[str],
        agents: Dict[str, Any],
        text: str,
        context_for_llm: str,
        pinned_files: List[str],
        request_node_id: str,
        node_path: str,
        request_timestamp: float,
        single_mode: bool,
    ) -> Dict[str, Any]:
        """
        Execute agent chain with context passing.

        Args:
            agents_to_call: List of agent names to call (e.g., ['PM', 'Dev', 'QA'])
            agents: Dictionary of agent configurations
            text: User message text
            context_for_llm: File context for LLM
            pinned_files: List of pinned file paths
            request_node_id: Node ID for request
            node_path: Path to the node
            request_timestamp: Timestamp of request
            single_mode: Whether in single agent mode

        Returns:
            Dictionary containing:
                - responses: List of agent response dictionaries
                - all_artifacts: List of extracted artifacts
                - previous_outputs: Dictionary of outputs keyed by agent name
        """
        responses = []
        previous_outputs = {}
        all_artifacts = []

        for agent_name in agents_to_call:
            if agent_name not in agents:
                continue

            agent_config = agents[agent_name]
            agent_instance = agent_config["instance"]
            system_prompt = agent_config["system_prompt"]

            if not agent_instance:
                print(f"[Agent] {agent_name}: Instance is None")
                continue

            print(f"[Agent] {agent_name}: Generating LLM response...")

            try:
                # Build pinned context with user query for relevance ranking
                agent_pinned_context = (
                    self.build_pinned_context(pinned_files, user_query=text)
                    if pinned_files
                    else ""
                )

                # Build prompt with chain context
                if self.ROLE_PROMPTS_AVAILABLE:
                    full_prompt = self.build_full_prompt(
                        agent_type=agent_name,
                        user_message=text,
                        file_context=context_for_llm,
                        previous_outputs=previous_outputs,
                        pinned_context=agent_pinned_context,
                    )
                    max_tokens = 999999  # Unlimited responses
                    print(
                        f"[Agent] {agent_name}: Using Phase 17-J chain-aware prompt (pinned: {len(pinned_files)} files)"
                    )
                else:
                    # Fallback prompt without chain context
                    full_prompt = f"""
{system_prompt}

{context_for_llm}

{agent_pinned_context}---
USER QUESTION: {text}
---

Provide your {agent_name} analysis:
"""
                    max_tokens = 500

                # Try streaming for single agent mode (first agent)
                use_streaming = (
                    single_mode and self.HOST_HAS_OLLAMA and len(responses) == 0
                )

                if use_streaming:
                    # Stream response for better UX
                    print(f"[Agent] {agent_name}: Using streaming mode")
                    model_for_stream = (
                        get_agent_model_name(agent_instance)
                        if agent_instance
                        else "qwen2.5vl:3b"
                    )
                    response_text, token_count = await self.stream_response(
                        self.sio,
                        self.sid,
                        full_prompt,
                        agent_name,
                        model_for_stream,
                        request_node_id,
                        node_path,
                    )
                    print(f"[Agent] {agent_name}: Streamed {token_count} tokens")
                else:
                    # Run sync LLM call in executor (non-streaming)
                    loop = asyncio.get_event_loop()
                    response_text = await loop.run_in_executor(
                        None,
                        lambda: agent_instance.call_llm(
                            prompt=full_prompt, max_tokens=max_tokens
                        ),
                    )

                    # Handle if response is dict
                    if isinstance(response_text, dict):
                        response_text = response_text.get(
                            "response", response_text.get("content", str(response_text))
                        )

                response_text = (
                    str(response_text)
                    if response_text
                    else f"[{agent_name}] No response generated"
                )

                print(f"[Agent] {agent_name}: Generated {len(response_text)} chars")

                # Save output for next agent
                previous_outputs[agent_name] = response_text

                # Extract artifacts from Dev
                if agent_name == "Dev" and self.ROLE_PROMPTS_AVAILABLE:
                    artifacts = self.extract_artifacts(response_text, agent_name)
                    if artifacts:
                        all_artifacts.extend(artifacts)
                        print(f"[Agent] Dev: Extracted {len(artifacts)} artifact(s)")
                        for artifact in artifacts:
                            print(
                                f"         -> {artifact['filename']} ({artifact['lines']} lines)"
                            )

                # Extract QA score
                if agent_name == "QA" and self.ROLE_PROMPTS_AVAILABLE:
                    qa_score = self.extract_qa_score(response_text)
                    qa_verdict = self.extract_qa_verdict(response_text)
                    if qa_score is not None:
                        print(
                            f"[Agent] QA: Score: {qa_score:.2f}/1.0, Verdict: {qa_verdict or 'N/A'}"
                        )

            except Exception as e:
                print(f"[Agent] {agent_name}: LLM error - {e}")
                response_text = f"[{agent_name}] Sorry, I encountered an error generating the response: {str(e)[:200]}"

            model_name = (
                get_agent_model_name(agent_instance) if agent_instance else "unknown"
            )

            responses.append(
                {
                    "agent": agent_name,
                    "model": model_name,
                    "text": response_text,
                    "node_id": request_node_id,
                    "node_path": node_path,
                    "timestamp": request_timestamp,
                }
            )

        return {
            "responses": responses,
            "all_artifacts": all_artifacts,
            "previous_outputs": previous_outputs,
        }
