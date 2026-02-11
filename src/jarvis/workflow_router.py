# MARKER_138.S2_2_WORKFLOW_ROUTER
"""Jarvis workflow routing for per-request superagent orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class WorkflowPlan:
    workflow: str
    phase_type: str
    preset: Optional[str]
    use_voice_pipeline: bool
    reasoning_depth: str
    tools: List[str]
    rationale: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "workflow": self.workflow,
            "phase_type": self.phase_type,
            "preset": self.preset,
            "use_voice_pipeline": self.use_voice_pipeline,
            "reasoning_depth": self.reasoning_depth,
            "tools": self.tools,
            "rationale": self.rationale,
        }


class JarvisWorkflowRouter:
    """Rule-based workflow router for Jarvis MCP requests."""

    RESEARCH_KEYWORDS = {"research", "find", "search", "look up", "analyze", "summary"}
    FIX_KEYWORDS = {"fix", "bug", "error", "broken", "issue", "debug"}
    BUILD_KEYWORDS = {"build", "implement", "create", "refactor", "write"}
    VOICE_KEYWORDS = {"voice", "speak", "audio", "microphone", "jarvis"}

    def route(self, request: str, voice_mode: bool = False) -> WorkflowPlan:
        text = (request or "").strip().lower()

        has_research = any(k in text for k in self.RESEARCH_KEYWORDS)
        has_fix = any(k in text for k in self.FIX_KEYWORDS)
        has_build = any(k in text for k in self.BUILD_KEYWORDS)
        has_voice = voice_mode or any(k in text for k in self.VOICE_KEYWORDS)

        if has_fix:
            return WorkflowPlan(
                workflow="jarvis_fix",
                phase_type="fix",
                preset="dragon_silver",
                use_voice_pipeline=has_voice,
                reasoning_depth="medium",
                tools=["search_semantic", "search_files", "read_file", "pipeline"],
                rationale="Detected bug/fix intent",
            )

        if has_build:
            return WorkflowPlan(
                workflow="jarvis_build",
                phase_type="build",
                preset="dragon_bronze",
                use_voice_pipeline=has_voice,
                reasoning_depth="medium",
                tools=["search_semantic", "search_files", "pipeline", "artifacts"],
                rationale="Detected implementation intent",
            )

        if has_research:
            return WorkflowPlan(
                workflow="jarvis_research",
                phase_type="research",
                preset=None,
                use_voice_pipeline=has_voice,
                reasoning_depth="high",
                tools=["unified_search", "search_semantic", "web_search"],
                rationale="Detected research/discovery intent",
            )

        return WorkflowPlan(
            workflow="jarvis_chat",
            phase_type="research",
            preset=None,
            use_voice_pipeline=has_voice,
            reasoning_depth="low",
            tools=["context", "chat"],
            rationale="Fallback conversational workflow",
        )
