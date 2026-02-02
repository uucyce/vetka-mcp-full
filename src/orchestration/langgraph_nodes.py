"""
VETKA LangGraph Node Implementations
Each node wraps existing agent/service functionality

@file langgraph_nodes.py
@status ACTIVE
@phase Phase 99 - STM Buffer Integration (prev: 75.5 Spatial Context)
@calledBy langgraph_builder.py
@lastAudit 2026-01-28

Node Functions:
- hostess_node: Entry point & routing decisions
- architect_node: Planning & task decomposition
- pm_node: Detailed planning
- dev_qa_parallel_node: Parallel Dev + QA execution
- eval_node: Quality gate (Phase 29 EvalAgent)
- learner_node: Failure analysis & retry (Phase 29 Self-Learning)
- approval_node: Final approval gate
"""

import asyncio
import re
import logging
import time
from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime

# Graceful import for langchain_core (allows tests without full langgraph install)
try:
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
except ImportError:
    # Fallback: import from our state module's mock
    from src.orchestration.langgraph_state import BaseMessage, HumanMessage, AIMessage

from src.orchestration.langgraph_state import (
    VETKAState,
    state_to_elisya_dict,
    add_agent_message,
    get_last_message_content,
    update_state_timestamp
)
from src.orchestration.event_types import (
    WorkflowEventEmitter,
    NodeStartedEvent,
    NodeCompletedEvent,
    NodeErrorEvent,
    NodeProgressEvent,
    ScoreComputedEvent,
    RetryDecisionEvent,
    LearnerAnalyzingEvent,
    LearnerSuggestionEvent,
    ArtifactCreatedEvent
)
# Phase 75.5: Context Fusion for spatial awareness
from src.orchestration.context_fusion import (
    build_context_for_hostess,
    build_context_for_dev
)

if TYPE_CHECKING:
    from src.orchestration.orchestrator_with_elisya import OrchestratorWithElisya
    from src.elisya.middleware import ElisyaMiddleware
    from src.orchestration.services import MemoryService, RoutingService, APIKeyService, CAMIntegration
    from src.agents.eval_agent import EvalAgent

logger = logging.getLogger(__name__)


class VETKANodes:
    """
    Collection of LangGraph nodes for VETKA workflow.

    Each node is a pure function: State -> State
    Nodes wrap existing orchestrator functionality for LangGraph compatibility.

    Design Principles:
    - Each node is stateless (receives state, returns modified state)
    - Nodes use existing services via orchestrator reference
    - Error handling is graceful (workflow continues on non-critical errors)
    - All async operations use proper awaits
    """

    # Score threshold for passing evaluation (from Grok research)
    EVAL_THRESHOLD = 0.75

    # Task keywords for routing decisions
    TASK_KEYWORDS = [
        'создай', 'напиши', 'сделай', 'реализуй', 'добавь', 'исправь',
        'implement', 'create', 'build', 'fix', 'add', 'write', 'develop',
        'refactor', 'optimize', 'deploy'
    ]

    def __init__(
        self,
        orchestrator: "OrchestratorWithElisya",
        event_emitter: WorkflowEventEmitter = None
    ):
        """
        Initialize nodes with orchestrator dependencies.

        Args:
            orchestrator: OrchestratorWithElisya instance with all services
            event_emitter: WorkflowEventEmitter for Socket.IO streaming (Phase 60.2)
        """
        self.orchestrator = orchestrator
        self.event_emitter = event_emitter or WorkflowEventEmitter()

        # Extract services for convenience
        self.memory = orchestrator.memory_service
        self.elisya = orchestrator.elisya_service
        self.routing = orchestrator.routing_service
        self.api_keys = orchestrator.key_service
        self.cam = orchestrator.cam_service

        # EvalAgent - lazy initialized
        self._eval_agent = None

        logger.info("[LangGraph] VETKANodes initialized with event emitter")

    @property
    def eval_agent(self) -> "EvalAgent":
        """Lazy-load EvalAgent."""
        if self._eval_agent is None:
            from src.agents.eval_agent import EvalAgent
            self._eval_agent = EvalAgent(memory_manager=self.memory.memory)
            logger.info("[LangGraph] EvalAgent lazy-initialized")
        return self._eval_agent

    # =========================================
    # HOSTESS NODE - Entry point & routing
    # =========================================

    async def hostess_node(self, state: VETKAState) -> VETKAState:
        """
        Hostess: Intelligent routing decision.

        Decides workflow path:
        - Simple questions → direct answer (end)
        - Complex tasks → delegate to architect
        - @mentions → route to specific agent

        Args:
            state: Current workflow state

        Returns:
            Updated state with routing decision in state['next']
        """
        start_time = time.time()
        workflow_id = state.get('workflow_id', 'unknown')

        # Emit: Node started
        await self.event_emitter.emit(NodeStartedEvent(
            workflow_id=workflow_id,
            node='hostess',
            input_preview=state.get('context', '')[:100]
        ))

        logger.info(f"[LangGraph] 🎀 Hostess node: analyzing request")

        try:
            # Get last message
            last_message = get_last_message_content(state)

            # Check for @mentions first
            mentions = self._parse_mentions(last_message)
            if mentions:
                state["mentions"] = mentions
                target = mentions[0].lower()
                # Map mention to node name
                mention_to_node = {
                    'pm': 'pm',
                    'dev': 'dev_qa_parallel',
                    'qa': 'dev_qa_parallel',
                    'architect': 'architect',
                    'researcher': 'architect',  # Researcher routes to architect for now
                }
                state["next"] = mention_to_node.get(target, 'architect')
                logger.info(f"[LangGraph] 🎀 @mention detected: {target} → {state['next']}")
                state["current_agent"] = "Hostess"

                # Emit: Node completed
                duration_ms = int((time.time() - start_time) * 1000)
                await self.event_emitter.emit(NodeCompletedEvent(
                    workflow_id=workflow_id,
                    node='hostess',
                    duration_ms=duration_ms,
                    next_node=state['next'],
                    output_preview=f"@mention: {target}"
                ))
                return update_state_timestamp(state)

            # Phase 75.5: Build fused spatial context for routing decision
            hostess_context = build_context_for_hostess(
                viewport_context=state.get('viewport_context'),
                pinned_files=state.get('pinned_files'),
                user_query=last_message
            )

            # Routing decision based on content analysis + spatial context
            decision = await self._hostess_decide(last_message, hostess_context or state.get("context", ""))

            if decision['action'] == 'answer':
                # Simple question - Hostess can answer directly
                state["agent_outputs"]["hostess"] = decision.get('response', '')
                state["next"] = "end"
                logger.info("[LangGraph] 🎀 Simple question → direct answer")
            elif decision['action'] == 'delegate':
                # Complex task - delegate to Architect
                state["next"] = "architect"
                logger.info("[LangGraph] 🎀 Complex task → architect")
            else:
                # Direct to specific agent
                state["next"] = decision.get('to', 'architect')
                logger.info(f"[LangGraph] 🎀 Direct route → {state['next']}")

            state["current_agent"] = "Hostess"

            # Emit: Node completed
            duration_ms = int((time.time() - start_time) * 1000)
            await self.event_emitter.emit(NodeCompletedEvent(
                workflow_id=workflow_id,
                node='hostess',
                duration_ms=duration_ms,
                next_node=state.get('next', 'architect'),
                output_preview=f"Route: {decision['action']}"
            ))

            return update_state_timestamp(state)

        except Exception as e:
            # Emit: Node error
            await self.event_emitter.emit(NodeErrorEvent(
                workflow_id=workflow_id,
                node='hostess',
                error_message=str(e),
                error_type=type(e).__name__
            ))
            raise

    async def _hostess_decide(self, message: str, context: str) -> Dict[str, Any]:
        """
        Hostess routing decision logic.

        Simple heuristics for now, can be enhanced with LLM later.
        """
        message_lower = message.lower()

        # Check if it's a task (needs full workflow)
        is_task = any(kw in message_lower for kw in self.TASK_KEYWORDS)

        # Check message length (longer messages usually need more work)
        is_complex = len(message) > 200

        if is_task or is_complex:
            return {'action': 'delegate', 'to': 'architect'}

        # Simple informational queries can be handled by Hostess
        # For now, delegate everything to architect for safety
        return {'action': 'delegate', 'to': 'architect'}

    def _parse_mentions(self, message: str) -> list:
        """Parse @mentions from message."""
        # MARKER_108_ROUTING_FIX_4: Support hyphenated model names (@gpt-5.2, @grok-4)
        mentions = re.findall(r'@([\w\-\.]+(?:/[\w\-\.]+)?(?::[\w\-\.]+)?)', message)
        valid_agents = ['pm', 'dev', 'qa', 'architect', 'researcher', 'hostess']
        return [m for m in mentions if m.lower() in valid_agents]

    # =========================================
    # ARCHITECT NODE - Planning & decomposition
    # =========================================

    async def architect_node(self, state: VETKAState) -> VETKAState:
        """
        Architect: Decompose task into subtasks, create plan.

        Architect analyzes the request and breaks it into actionable tasks
        that PM, Dev, and QA can work on.
        """
        start_time = time.time()
        workflow_id = state.get('workflow_id', 'unknown')

        # Emit: Node started
        await self.event_emitter.emit(NodeStartedEvent(
            workflow_id=workflow_id,
            node='architect',
            input_preview=state.get('context', '')[:100]
        ))

        logger.info(f"[LangGraph] 🏗️ Architect node: planning")

        try:
            # Convert to ElisyaState for backwards compatibility
            elisya_state = self._create_elisya_state(state)

            # Reframe context for Architect
            elisya_state = self.elisya.reframe_context(elisya_state, 'Architect')

            # Execute Architect agent
            try:
                output, _ = await self.orchestrator._run_agent_with_elisya_async(
                    agent_type='Architect',
                    state=elisya_state,
                    prompt=elisya_state.context or state["context"]
                )
            except Exception as e:
                logger.error(f"[LangGraph] Architect execution failed: {e}")
                output = f"Error in Architect: {str(e)}"

            # Parse tasks from output
            tasks = self._parse_tasks(output)

            # Update state
            state["agent_outputs"]["architect"] = output
            state["tasks"] = tasks
            state["current_agent"] = "Architect"
            state["next"] = "pm"

            # Add message
            state["messages"] = add_agent_message(state, "Architect", output)

            # Emit: Node completed
            duration_ms = int((time.time() - start_time) * 1000)
            await self.event_emitter.emit(NodeCompletedEvent(
                workflow_id=workflow_id,
                node='architect',
                duration_ms=duration_ms,
                next_node='pm',
                output_preview=output[:100] if output else '',
                artifacts_created=len(tasks)
            ))

            logger.info(f"[LangGraph] 🏗️ Architect: {len(tasks)} tasks identified")
            return update_state_timestamp(state)

        except Exception as e:
            await self.event_emitter.emit(NodeErrorEvent(
                workflow_id=workflow_id,
                node='architect',
                error_message=str(e),
                error_type=type(e).__name__
            ))
            raise

    def _parse_tasks(self, architect_output: str) -> list:
        """Parse tasks from Architect output."""
        tasks = []
        lines = architect_output.split('\n')

        for line in lines:
            stripped = line.strip()
            # Match bullet points or numbered lists
            if stripped.startswith(('- ', '* ', '• ')):
                tasks.append({'description': stripped[2:].strip(), 'status': 'pending'})
            elif re.match(r'^\d+[\.\)]\s', stripped):
                task_text = re.sub(r'^\d+[\.\)]\s*', '', stripped)
                tasks.append({'description': task_text, 'status': 'pending'})

        # If no tasks found, create a default one
        if not tasks:
            tasks.append({'description': 'Complete the requested task', 'status': 'pending'})

        return tasks

    # =========================================
    # PM NODE - Detailed planning
    # =========================================

    async def pm_node(self, state: VETKAState) -> VETKAState:
        """
        PM: Create detailed plan from Architect's decomposition.

        PM takes the high-level architecture and creates specific
        implementation steps for Dev and QA.
        """
        start_time = time.time()
        workflow_id = state.get('workflow_id', 'unknown')

        # Emit: Node started
        await self.event_emitter.emit(NodeStartedEvent(
            workflow_id=workflow_id,
            node='pm',
            input_preview=state["agent_outputs"].get("architect", "")[:100]
        ))

        logger.info(f"[LangGraph] 📋 PM node: detailed planning")

        try:
            # Convert to ElisyaState
            elisya_state = self._create_elisya_state(state)

            # Add Architect output to context
            architect_output = state["agent_outputs"].get("architect", "")
            if architect_output:
                elisya_state.context = f"{state['context']}\n\n## Architecture Plan:\n{architect_output}"

            # Reframe for PM
            elisya_state = self.elisya.reframe_context(elisya_state, 'PM')

            # Execute PM agent
            try:
                output, _ = await self.orchestrator._run_agent_with_elisya_async(
                    agent_type='PM',
                    state=elisya_state,
                    prompt=elisya_state.context or state["context"]
                )
            except Exception as e:
                logger.error(f"[LangGraph] PM execution failed: {e}")
                output = f"Error in PM: {str(e)}"

            # Update state
            state["agent_outputs"]["pm"] = output
            state["current_agent"] = "PM"
            state["next"] = "dev_qa_parallel"

            # Add message
            state["messages"] = add_agent_message(state, "PM", output)

            # Emit: Node completed
            duration_ms = int((time.time() - start_time) * 1000)
            await self.event_emitter.emit(NodeCompletedEvent(
                workflow_id=workflow_id,
                node='pm',
                duration_ms=duration_ms,
                next_node='dev_qa_parallel',
                output_preview=output[:100] if output else ''
            ))

            logger.info("[LangGraph] 📋 PM: detailed plan created")
            return update_state_timestamp(state)

        except Exception as e:
            await self.event_emitter.emit(NodeErrorEvent(
                workflow_id=workflow_id,
                node='pm',
                error_message=str(e),
                error_type=type(e).__name__
            ))
            raise

    # =========================================
    # HOPE ENHANCEMENT NODE - Phase 76.2
    # =========================================

    async def hope_enhancement_node(self, state: VETKAState) -> VETKAState:
        """
        HOPE (Hierarchical Observation Processing Engine) enhancement.

        Phase 76.2: Analyzes PM output with multi-frequency approach:
        - LOW level (~200 words): High-level overview
        - MID level (~400 words): Relationships & patterns
        - HIGH level (~600 words): Fine-grained details

        Marker: [M-10] - Insert between pm_node and dev_qa_parallel_node

        The analysis is injected into Dev+QA context for better understanding.
        """
        start_time = time.time()
        workflow_id = state.get('workflow_id', 'unknown')
        lod_level = state.get('lod_level', 'MEDIUM')

        # Emit: Node started
        await self.event_emitter.emit(NodeStartedEvent(
            workflow_id=workflow_id,
            node='hope_enhancement',
            input_preview=f"LOD: {lod_level}"
        ))

        logger.info(f"[LangGraph] 🧠 HOPE enhancement node (LOD: {lod_level})")

        try:
            # Get PM output for analysis
            pm_output = state.get('agent_outputs', {}).get('pm', '')
            architect_output = state.get('agent_outputs', {}).get('architect', '')

            # Combine context for HOPE analysis
            content_to_analyze = f"{state.get('context', '')}\n\n"
            if architect_output:
                content_to_analyze += f"## Architecture:\n{architect_output[:2000]}\n\n"
            if pm_output:
                content_to_analyze += f"## Plan:\n{pm_output[:2000]}\n\n"

            # Map LOD to HOPE complexity
            complexity_map = {
                'MICRO': 'LOW',
                'SMALL': 'LOW',
                'MEDIUM': 'MID',
                'LARGE': 'HIGH',
                'EPIC': 'HIGH'
            }
            complexity = complexity_map.get(lod_level, 'MID')

            # Initialize HOPE enhancer
            try:
                from src.agents.hope_enhancer import HOPEEnhancer, FrequencyLayer

                hope = HOPEEnhancer(use_api_fallback=False)  # Use local only for speed

                # Determine layers based on complexity
                if complexity == 'LOW':
                    layers = [FrequencyLayer.LOW]
                elif complexity == 'MID':
                    layers = [FrequencyLayer.LOW, FrequencyLayer.MID]
                else:
                    layers = [FrequencyLayer.LOW, FrequencyLayer.MID, FrequencyLayer.HIGH]

                # Analyze
                analysis = hope.analyze(
                    content=content_to_analyze[:4000],  # Limit for context window
                    layers=layers,
                    complexity=lod_level,
                    cache_key=workflow_id
                )

                # Extract summary
                hope_summary = analysis.get('combined', '')
                if not hope_summary:
                    hope_summary = analysis.get('low', '') or ''

                # Store in state
                state['hope_analysis'] = analysis
                state['hope_summary'] = hope_summary

                # FIX_99.1: Add HOPE summary to STM buffer
                try:
                    from src.memory.stm_buffer import STMBuffer, STMEntry
                    stm_data = state.get('stm_buffer')
                    if stm_data:
                        stm = STMBuffer.from_dict(stm_data)
                    else:
                        stm = STMBuffer(max_size=10, decay_rate=0.1)
                    stm.add_from_hope(hope_summary[:500], workflow_id=workflow_id)
                    state['stm_buffer'] = stm.to_dict()
                    logger.debug(f"[LangGraph] STM updated with HOPE summary")
                except Exception as stm_error:
                    logger.warning(f"[LangGraph] STM update failed: {stm_error}")

                logger.info(f"[LangGraph] 🧠 HOPE analysis complete: {len(hope_summary)} chars, layers: {[l.name for l in layers]}")

            except ImportError as e:
                logger.warning(f"[LangGraph] HOPE module not available: {e}")
                state['hope_analysis'] = {}
                state['hope_summary'] = ''
            except Exception as e:
                logger.warning(f"[LangGraph] HOPE analysis failed: {e}")
                state['hope_analysis'] = {}
                state['hope_summary'] = ''

            # Update state for next node
            state["current_agent"] = "HOPE"
            state["next"] = "dev_qa_parallel"

            # Emit: Node completed
            duration_ms = int((time.time() - start_time) * 1000)
            await self.event_emitter.emit(NodeCompletedEvent(
                workflow_id=workflow_id,
                node='hope_enhancement',
                duration_ms=duration_ms,
                next_node='dev_qa_parallel',
                output_preview=f"HOPE summary: {len(state.get('hope_summary', ''))} chars"
            ))

            return update_state_timestamp(state)

        except Exception as e:
            logger.error(f"[LangGraph] HOPE enhancement failed: {e}")
            # Don't fail the workflow, just continue without HOPE
            state['hope_analysis'] = {}
            state['hope_summary'] = ''
            state["next"] = "dev_qa_parallel"

            await self.event_emitter.emit(NodeErrorEvent(
                workflow_id=workflow_id,
                node='hope_enhancement',
                error_message=str(e),
                error_type=type(e).__name__
            ))

            return update_state_timestamp(state)

    # =========================================
    # DEV + QA PARALLEL NODE
    # =========================================

    async def dev_qa_parallel_node(self, state: VETKAState) -> VETKAState:
        """
        Dev + QA: Execute in parallel.

        Dev implements the solution while QA prepares tests.
        Both run concurrently to save time.
        """
        start_time = time.time()
        workflow_id = state.get('workflow_id', 'unknown')

        # Emit: Node started
        await self.event_emitter.emit(NodeStartedEvent(
            workflow_id=workflow_id,
            node='dev_qa_parallel',
            retry_attempt=state['retry_count'],
            input_preview=state["agent_outputs"].get("pm", "")[:100]
        ))

        logger.info(f"[LangGraph] 👨‍💻🔍 Dev + QA parallel node (retry {state['retry_count']})")

        try:
            # Prepare context with previous agent outputs
            base_context = state["context"]
            pm_output = state["agent_outputs"].get("pm", "")
            architect_output = state["agent_outputs"].get("architect", "")

            combined_context = f"{base_context}\n\n"
            if architect_output:
                combined_context += f"## Architecture:\n{architect_output}\n\n"
            if pm_output:
                combined_context += f"## Detailed Plan:\n{pm_output}\n\n"

            # Phase 75.5: Inject fused spatial + code context
            code_context = {
                'summary': 'Dev/QA parallel execution',
                'last_operation': 'executing',
                'files_modified': [],
            }
            dev_spatial_context = build_context_for_dev(
                viewport_context=state.get('viewport_context'),
                pinned_files=state.get('pinned_files'),
                code_context=code_context,
                user_query=base_context
            )
            if dev_spatial_context:
                combined_context = f"{dev_spatial_context}\n\n{combined_context}"

            # Phase 76.2: Inject HOPE hierarchical analysis
            hope_summary = state.get('hope_summary', '')
            if hope_summary:
                combined_context = f"## 🧠 HOPE Analysis (Hierarchical Overview)\n{hope_summary}\n\n{combined_context}"
                logger.debug(f"[LangGraph] HOPE context injected: {len(hope_summary)} chars")

            # If this is a retry, add feedback and enhanced prompt
            if state["retry_count"] > 0:
                eval_feedback = state.get("eval_feedback", "")
                enhanced_prompt = state.get("enhanced_prompt", "")

                combined_context += f"""
### ⚠️ RETRY #{state['retry_count']} - Previous Issues:
{eval_feedback}

### 💡 Improvement Suggestions:
{enhanced_prompt}

Please address these issues in your implementation.
"""
                logger.info(f"[LangGraph] Dev+QA: retry mode with enhanced context")

            # Create ElisyaStates for each agent
            dev_state = self._create_elisya_state(state)
            dev_state.context = combined_context
            dev_state = self.elisya.reframe_context(dev_state, 'Dev')

            qa_state = self._create_elisya_state(state)
            qa_state.context = combined_context
            qa_state = self.elisya.reframe_context(qa_state, 'QA')

            # Emit: Progress - starting parallel execution
            await self.event_emitter.emit(NodeProgressEvent(
                workflow_id=workflow_id,
                node='dev_qa_parallel',
                progress_percent=10,
                status_message='Starting Dev and QA in parallel'
            ))

            # Execute in parallel
            dev_task = self.orchestrator._run_agent_with_elisya_async(
                agent_type='Dev',
                state=dev_state,
                prompt=dev_state.context or combined_context
            )

            qa_task = self.orchestrator._run_agent_with_elisya_async(
                agent_type='QA',
                state=qa_state,
                prompt=qa_state.context or combined_context
            )

            # Wait for both
            try:
                results = await asyncio.gather(dev_task, qa_task, return_exceptions=True)

                # Process results
                dev_output = results[0][0] if isinstance(results[0], tuple) else f"Dev error: {results[0]}"
                qa_output = results[1][0] if isinstance(results[1], tuple) else f"QA error: {results[1]}"

            except Exception as e:
                logger.error(f"[LangGraph] Dev+QA parallel execution failed: {e}")
                dev_output = f"Dev execution failed: {str(e)}"
                qa_output = f"QA execution failed: {str(e)}"

            # Update state
            state["agent_outputs"]["dev"] = dev_output
            state["agent_outputs"]["qa"] = qa_output
            state["current_agent"] = "Dev+QA"
            state["next"] = "eval"

            # Add messages
            state["messages"] = add_agent_message(state, "Dev", dev_output)
            state["messages"] = add_agent_message(state, "QA", qa_output)

            # Emit: Node completed
            duration_ms = int((time.time() - start_time) * 1000)
            await self.event_emitter.emit(NodeCompletedEvent(
                workflow_id=workflow_id,
                node='dev_qa_parallel',
                duration_ms=duration_ms,
                next_node='eval',
                output_preview=f"Dev: {len(dev_output)} chars, QA: {len(qa_output)} chars"
            ))

            logger.info("[LangGraph] 👨‍💻🔍 Dev + QA: parallel execution complete")
            return update_state_timestamp(state)

        except Exception as e:
            await self.event_emitter.emit(NodeErrorEvent(
                workflow_id=workflow_id,
                node='dev_qa_parallel',
                error_message=str(e),
                error_type=type(e).__name__
            ))
            raise

    # =========================================
    # EVAL NODE - Quality gate (Phase 29)
    # =========================================

    async def eval_node(self, state: VETKAState) -> VETKAState:
        """
        EvalAgent: Score the output, decide retry or continue.

        Threshold: 0.75 (from Grok research - optimal for quality/cost)

        Evaluation Criteria:
        - Correctness (40%): Does it meet requirements?
        - Completeness (30%): Is it thorough?
        - Code Quality (20%): Is it well-structured?
        - Clarity (10%): Is it understandable?
        """
        start_time = time.time()
        workflow_id = state.get('workflow_id', 'unknown')

        # Emit: Node started
        await self.event_emitter.emit(NodeStartedEvent(
            workflow_id=workflow_id,
            node='eval',
            retry_attempt=state.get('retry_count', 0)
        ))

        logger.info(f"[LangGraph] ⭐ Eval node: scoring (attempt {state['retry_count'] + 1})")

        try:
            # Combine Dev + QA outputs for evaluation
            dev_output = state["agent_outputs"].get("dev", "")
            qa_output = state["agent_outputs"].get("qa", "")

            combined_output = f"""
## Developer Output:
{dev_output}

## QA Output:
{qa_output}
"""

            # Determine complexity from LOD level
            lod_to_complexity = {
                'MICRO': 'MICRO',
                'SMALL': 'SMALL',
                'MEDIUM': 'MEDIUM',
                'LARGE': 'LARGE',
                'EPIC': 'EPIC'
            }
            complexity = lod_to_complexity.get(state.get("lod_level", "MEDIUM"), "MEDIUM")

            # Call EvalAgent
            try:
                eval_result = self.eval_agent.evaluate(
                    task=state["raw_context"],
                    output=combined_output,
                    complexity=complexity,
                    reference=state.get("context", "")
                )

                score = eval_result.get('score', 0.5)
                feedback = eval_result.get('feedback', 'No feedback available')

            except Exception as e:
                logger.error(f"[LangGraph] EvalAgent failed: {e}")
                score = 0.5  # Neutral score on failure
                feedback = f"Evaluation failed: {str(e)}"
                eval_result = {'score': score, 'feedback': feedback}

            # Update state
            state["eval_score"] = score
            state["eval_feedback"] = feedback
            state["current_agent"] = "EvalAgent"

            # Emit: Score computed (Phase 29 specific!)
            await self.event_emitter.emit(ScoreComputedEvent(
                workflow_id=workflow_id,
                score=score,
                threshold=self.EVAL_THRESHOLD,
                feedback_preview=feedback[:200] if feedback else ''
            ))

            # Routing decision based on score
            will_retry = False
            if score >= self.EVAL_THRESHOLD:
                state["next"] = "approval"
                logger.info(f"[LangGraph] ✅ Score {score:.2f} >= {self.EVAL_THRESHOLD} → approval")
            elif state["retry_count"] < state["max_retries"]:
                state["next"] = "learner"
                will_retry = True
                logger.info(f"[LangGraph] ⚠️ Score {score:.2f} < {self.EVAL_THRESHOLD}, retry {state['retry_count'] + 1}/{state['max_retries']} → learner")
            else:
                # Max retries reached, proceed anyway with warning
                state["next"] = "approval"
                logger.warning(f"[LangGraph] ❌ Max retries reached, score {score:.2f} → approval (with warning)")
                state["eval_feedback"] += "\n\n⚠️ Note: Maximum retries reached. Output may need manual review."

            # Emit: Retry decision (Phase 29 specific!)
            await self.event_emitter.emit(RetryDecisionEvent(
                workflow_id=workflow_id,
                will_retry=will_retry,
                retry_count=state['retry_count'],
                max_retries=state['max_retries']
            ))

            # Emit: Node completed
            duration_ms = int((time.time() - start_time) * 1000)
            await self.event_emitter.emit(NodeCompletedEvent(
                workflow_id=workflow_id,
                node='eval',
                duration_ms=duration_ms,
                next_node=state.get('next', 'approval'),
                output_preview=f"Score: {score:.2f}"
            ))

            return update_state_timestamp(state)

        except Exception as e:
            await self.event_emitter.emit(NodeErrorEvent(
                workflow_id=workflow_id,
                node='eval',
                error_message=str(e),
                error_type=type(e).__name__
            ))
            raise

    # =========================================
    # LEARNER NODE - Phase 29 Self-Learning!
    # =========================================

    async def learner_node(self, state: VETKAState) -> VETKAState:
        """
        LearnerAgent: Analyze failure, suggest improvements.

        THIS IS THE HEART OF PHASE 29!

        LearnerAgent:
        1. Categorizes the failure
        2. Identifies root cause
        3. Generates enhanced prompt for retry
        4. Stores lessons for future learning
        """
        start_time = time.time()
        workflow_id = state.get('workflow_id', 'unknown')

        # Emit: Node started
        await self.event_emitter.emit(NodeStartedEvent(
            workflow_id=workflow_id,
            node='learner',
            retry_attempt=state.get('retry_count', 0)
        ))

        logger.info(f"[LangGraph] 🧠 Learner node: analyzing failure")

        try:
            # Emit: Analyzing
            await self.event_emitter.emit(LearnerAnalyzingEvent(
                workflow_id=workflow_id,
                analyzing_what="Evaluating failure patterns and generating improvements"
            ))

            # Import LearnerAgent
            from src.agents.learner_agent import LearnerAgent

            learner = LearnerAgent(memory_manager=self.memory.memory)

            # Analyze failure
            try:
                analysis = await learner.analyze_failure(
                    task=state["raw_context"],
                    output=state["agent_outputs"].get("dev", ""),
                    eval_feedback=state["eval_feedback"],
                    retry_count=state["retry_count"]
                )
            except Exception as e:
                logger.error(f"[LangGraph] LearnerAgent failed: {e}")
                analysis = {
                    'failure_category': 'unknown',
                    'root_cause': str(e),
                    'improvement_suggestion': 'Please review and try again.',
                    'enhanced_prompt': state["eval_feedback"],
                    'confidence': 0.3
                }

            # Update state
            state["failure_analysis"] = analysis
            state["enhanced_prompt"] = analysis.get('enhanced_prompt', '')

            # Store lesson
            state["lessons_learned"].append({
                'task': state["raw_context"][:100],
                'failure_reason': analysis.get('failure_category', 'unknown'),
                'suggestion': analysis.get('improvement_suggestion', ''),
                'retry_attempt': state["retry_count"]
            })

            # Emit: Suggestion ready (Phase 29 specific!)
            await self.event_emitter.emit(LearnerSuggestionEvent(
                workflow_id=workflow_id,
                failure_category=analysis.get('failure_category', 'unknown'),
                suggestion_preview=analysis.get('improvement_suggestion', '')[:200],
                confidence=analysis.get('confidence', 0.0),
                similar_failures_found=len(analysis.get('similar_failures', []))
            ))

            # Increment retry counter
            state["retry_count"] += 1
            state["current_agent"] = "Learner"
            state["next"] = "dev_qa_parallel"  # Loop back!

            suggestion = analysis.get('improvement_suggestion', '')[:100]
            logger.info(f"[LangGraph] 🔄 Learner suggests: {suggestion}...")

            # Emit: Node completed
            duration_ms = int((time.time() - start_time) * 1000)
            await self.event_emitter.emit(NodeCompletedEvent(
                workflow_id=workflow_id,
                node='learner',
                duration_ms=duration_ms,
                next_node='dev_qa_parallel',
                output_preview=f"Category: {analysis.get('failure_category', 'unknown')}"
            ))

            return update_state_timestamp(state)

        except Exception as e:
            await self.event_emitter.emit(NodeErrorEvent(
                workflow_id=workflow_id,
                node='learner',
                error_message=str(e),
                error_type=type(e).__name__
            ))
            raise

    # =========================================
    # APPROVAL NODE
    # =========================================

    async def approval_node(self, state: VETKAState) -> VETKAState:
        """
        Approval: Final gate before completion.

        - Stores successful workflow in memory
        - Processes artifacts via CAM
        - Prepares final response
        """
        start_time = time.time()
        workflow_id = state.get('workflow_id', 'unknown')

        # Emit: Node started
        await self.event_emitter.emit(NodeStartedEvent(
            workflow_id=workflow_id,
            node='approval',
            input_preview=f"Score: {state.get('eval_score', 0):.2f}"
        ))

        logger.info(f"[LangGraph] ✅ Approval node: finalizing")

        try:
            # Store successful workflow in memory
            if state["eval_score"] >= self.EVAL_THRESHOLD:
                try:
                    self.memory.memory.triple_write({
                        "type": "workflow_success",
                        "workflow_id": state["workflow_id"],
                        "task": state["raw_context"][:500],
                        "score": state["eval_score"],
                        "agents_used": list(state["agent_outputs"].keys()),
                        "retries": state["retry_count"],
                        "speaker": "system"
                    })
                    logger.info("[LangGraph] ✅ Workflow stored in memory")
                except Exception as e:
                    logger.warning(f"[LangGraph] Failed to store workflow: {e}")

            # Process artifacts via CAM
            artifacts_processed = 0
            for artifact in state.get("artifacts", []):
                try:
                    if self.cam.is_available():
                        await self.cam.process_artifact(artifact)
                        artifacts_processed += 1

                        # Emit: Artifact created
                        await self.event_emitter.emit(ArtifactCreatedEvent(
                            workflow_id=workflow_id,
                            artifact_id=artifact.get('id', 'unknown'),
                            artifact_type=artifact.get('type', 'unknown'),
                            artifact_name=artifact.get('name', 'unnamed'),
                            created_by='approval'
                        ))
                except Exception as e:
                    logger.warning(f"[LangGraph] CAM artifact processing failed: {e}")

            # Store lessons learned if any retries happened
            if state["retry_count"] > 0 and state["lessons_learned"]:
                try:
                    for lesson in state["lessons_learned"]:
                        self.memory.memory.triple_write({
                            "type": "lesson_learned",
                            "workflow_id": state["workflow_id"],
                            **lesson,
                            "final_score": state["eval_score"],
                            "speaker": "learner"
                        })
                    logger.info(f"[LangGraph] 📚 {len(state['lessons_learned'])} lessons stored")
                except Exception as e:
                    logger.warning(f"[LangGraph] Failed to store lessons: {e}")

            # === PHASE 76.1: Store in Replay Buffer + Increment Counter ===
            try:
                # Store example in Replay Buffer for LoRA training
                if hasattr(self.orchestrator, 'replay_buffer') and self.orchestrator.replay_buffer:
                    # Get embeddings for the task
                    from src.utils.embedding_service import get_embedding_service
                    emb_service = get_embedding_service()

                    if emb_service:
                        task_embedding = emb_service.get_embedding(state["raw_context"][:1000])

                        if task_embedding and len(task_embedding) == 768:
                            example = {
                                'workflow_id': state['workflow_id'],
                                'task': state['raw_context'][:1000],
                                'enhanced_prompt': state.get('enhanced_prompt', ''),
                                'eval_score': state.get('eval_score', 0.0),
                                'retry_count': state.get('retry_count', 0),
                                'surprise_score': state.get('surprise_scores', {}).get('overall', 0.5),
                                'embeddings': task_embedding
                            }

                            if self.orchestrator.replay_buffer.add(example):
                                logger.debug(f"[Phase76.1] Example added to Replay Buffer")

                # Increment workflow counter for LoRA trigger
                if hasattr(self.orchestrator, 'increment_workflow_counter'):
                    counter_result = self.orchestrator.increment_workflow_counter(
                        eval_score=state.get('eval_score', 0.0)
                    )
                    if counter_result.get('lora_trigger'):
                        logger.info(f"[Phase76.1] LoRA trigger at workflow {counter_result.get('counter')}")

            except Exception as e:
                logger.debug(f"[Phase76.1] Replay/Counter integration: {e}")

            state["current_agent"] = "Approval"
            state["next"] = "end"

            # Emit: Node completed
            duration_ms = int((time.time() - start_time) * 1000)
            await self.event_emitter.emit(NodeCompletedEvent(
                workflow_id=workflow_id,
                node='approval',
                duration_ms=duration_ms,
                next_node='end',
                output_preview=f"Approved, {artifacts_processed} artifacts",
                artifacts_created=artifacts_processed
            ))

            logger.info(f"[LangGraph] ✅ Workflow approved (score: {state['eval_score']:.2f}, retries: {state['retry_count']})")
            return update_state_timestamp(state)

        except Exception as e:
            await self.event_emitter.emit(NodeErrorEvent(
                workflow_id=workflow_id,
                node='approval',
                error_message=str(e),
                error_type=type(e).__name__
            ))
            raise

    # =========================================
    # HELPER METHODS
    # =========================================

    def _create_elisya_state(self, state: VETKAState):
        """
        Create ElisyaState from VETKAState for backwards compatibility.

        This allows existing agent code to work unchanged.
        """
        from src.elisya.state import ElisyaState

        return ElisyaState(
            workflow_id=state["workflow_id"],
            speaker=state.get("current_agent", "PM"),
            context=state.get("context", ""),
            raw_context=state.get("raw_context", ""),
            semantic_path=state.get("semantic_path", ""),
            lod_level=state.get("lod_level", "tree").lower(),
            retry_count=state.get("retry_count", 0),
            score=state.get("eval_score", 0.0)
        )
