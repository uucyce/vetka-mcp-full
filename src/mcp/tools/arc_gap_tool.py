"""
VETKA MCP Tool - ARC Gap Detection

Detects conceptual gaps in prompts using ARC methodology.
Helps agents and users identify missing connections before execution.

@status: active
@phase: 99.3
@depends: base_tool, arc_gap_detector, arc_solver_agent
@used_by: mcp_server, stdio_server, vetka_mcp_bridge
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional

from .base_tool import BaseMCPTool

logger = logging.getLogger(__name__)


class ARCGapTool(BaseMCPTool):
    """
    MCP Tool for ARC-based conceptual gap detection.

    Analyzes prompts/context to find missing concepts that could
    improve agent outputs. Uses:
    - Pattern-based concept extraction
    - Semantic search for related concepts
    - ARC Solver for deep reasoning
    """

    def __init__(self):
        self._detector = None
        self._memory = None
        self._arc_solver = None

    def _get_detector(self):
        """Lazy load gap detector with dependencies."""
        if self._detector is None:
            try:
                from src.orchestration.arc_gap_detector import ARCGapDetector
                from src.initialization.singletons import get_memory_manager

                # Get memory manager for semantic search
                try:
                    self._memory = get_memory_manager()
                except Exception:
                    self._memory = None

                # Get ARC Solver if available
                try:
                    from src.initialization.singletons import get_arc_solver
                    self._arc_solver = get_arc_solver()
                except Exception:
                    self._arc_solver = None

                self._detector = ARCGapDetector(
                    memory_manager=self._memory,
                    arc_solver=self._arc_solver,
                    min_confidence=0.3,
                    max_suggestions=5
                )
                logger.debug("ARCGapTool detector initialized")

            except ImportError as e:
                logger.warning(f"Failed to import ARCGapDetector: {e}")
            except Exception as e:
                logger.warning(f"Failed to initialize ARCGapTool: {e}")

        return self._detector

    @property
    def name(self) -> str:
        return "vetka_arc_gap"

    @property
    def description(self) -> str:
        return (
            "Analyze prompt/context for conceptual gaps using ARC methodology. "
            "Returns suggestions for missing connections, patterns, or concepts "
            "that could improve the quality of agent responses."
        )

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The prompt or request to analyze for gaps"
                },
                "context": {
                    "type": "string",
                    "default": "",
                    "description": "Additional context (file content, previous messages, etc.)"
                },
                "include_arc_reasoning": {
                    "type": "boolean",
                    "default": True,
                    "description": "Use ARC Solver for deep pattern analysis (slower but better)"
                },
                "max_suggestions": {
                    "type": "integer",
                    "default": 3,
                    "description": "Maximum number of suggestions to return (1-10)"
                },
                "min_confidence": {
                    "type": "number",
                    "default": 0.3,
                    "description": "Minimum confidence threshold for suggestions (0.0-1.0)"
                }
            },
            "required": ["prompt"]
        }

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute gap detection analysis.

        Args:
            arguments: {
                prompt: str - The prompt to analyze
                context: str - Additional context
                include_arc_reasoning: bool - Use ARC Solver
                max_suggestions: int - Max suggestions
                min_confidence: float - Min confidence
            }

        Returns:
            {
                success: bool,
                gaps: List[Dict] - Detected gaps with suggestions,
                extracted_concepts: List[str] - Concepts found in prompt,
                suggestions_text: str - Formatted text for prompt injection,
                stats: Dict - Analysis statistics
            }
        """
        prompt = arguments.get("prompt", "")
        context = arguments.get("context", "")
        include_arc = arguments.get("include_arc_reasoning", True)
        max_sugg = min(10, max(1, arguments.get("max_suggestions", 3)))
        min_conf = max(0.0, min(1.0, arguments.get("min_confidence", 0.3)))

        if not prompt:
            return {
                "success": False,
                "error": "prompt is required",
                "gaps": [],
                "extracted_concepts": [],
                "suggestions_text": ""
            }

        detector = self._get_detector()
        if not detector:
            return {
                "success": False,
                "error": "ARCGapDetector not available",
                "gaps": [],
                "extracted_concepts": [],
                "suggestions_text": ""
            }

        try:
            # Update detector settings
            detector.max_suggestions = max_sugg
            detector.min_confidence = min_conf

            # Temporarily disable ARC Solver if not requested
            original_arc = detector.arc_solver
            if not include_arc:
                detector.arc_solver = None

            # Run analysis
            result = await detector.analyze(prompt, context)

            # Restore ARC Solver
            if not include_arc:
                detector.arc_solver = original_arc

            # Format gaps for response
            gaps_list = [
                {
                    "concept": gap.concept,
                    "related_concepts": gap.related_concepts,
                    "gap_type": gap.gap_type,
                    "confidence": gap.confidence,
                    "suggestion": gap.suggestion,
                    "source": gap.source
                }
                for gap in result.gaps
            ]

            return {
                "success": True,
                "gaps": gaps_list,
                "extracted_concepts": result.extracted_concepts,
                "related_found": result.related_found,
                "suggestions_text": result.suggestions_text,
                "stats": {
                    "concepts_extracted": len(result.extracted_concepts),
                    "gaps_found": len(result.gaps),
                    "arc_enabled": include_arc and self._arc_solver is not None,
                    "memory_enabled": self._memory is not None
                }
            }

        except Exception as e:
            logger.error(f"ARCGapTool execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "gaps": [],
                "extracted_concepts": [],
                "suggestions_text": ""
            }


class ARCConceptsTool(BaseMCPTool):
    """
    Simple tool to extract concepts from text without full gap analysis.
    Lightweight alternative when only concept extraction is needed.
    """

    def __init__(self):
        self._detector = None

    def _get_detector(self):
        if self._detector is None:
            try:
                from src.orchestration.arc_gap_detector import ARCGapDetector
                self._detector = ARCGapDetector()
            except Exception as e:
                logger.warning(f"Failed to initialize ARCConceptsTool: {e}")
        return self._detector

    @property
    def name(self) -> str:
        return "vetka_arc_concepts"

    @property
    def description(self) -> str:
        return "Extract key concepts from text using pattern matching (fast, no LLM calls)"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to extract concepts from"
                }
            },
            "required": ["text"]
        }

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        text = arguments.get("text", "")

        if not text:
            return {"success": False, "error": "text is required", "concepts": []}

        detector = self._get_detector()
        if not detector:
            return {"success": False, "error": "Detector not available", "concepts": []}

        try:
            concepts = detector.extract_concepts(text)
            return {
                "success": True,
                "concepts": concepts,
                "count": len(concepts)
            }
        except Exception as e:
            return {"success": False, "error": str(e), "concepts": []}


# === Convenience functions for direct MCP registration ===

_arc_gap_tool: Optional[ARCGapTool] = None
_arc_concepts_tool: Optional[ARCConceptsTool] = None


def get_arc_gap_tool() -> ARCGapTool:
    """Get singleton ARC Gap Tool instance."""
    global _arc_gap_tool
    if _arc_gap_tool is None:
        _arc_gap_tool = ARCGapTool()
    return _arc_gap_tool


def get_arc_concepts_tool() -> ARCConceptsTool:
    """Get singleton ARC Concepts Tool instance."""
    global _arc_concepts_tool
    if _arc_concepts_tool is None:
        _arc_concepts_tool = ARCConceptsTool()
    return _arc_concepts_tool


async def vetka_arc_gap(prompt: str, context: str = "", **kwargs) -> Dict[str, Any]:
    """Direct function call for gap detection."""
    tool = get_arc_gap_tool()
    return await tool.execute({"prompt": prompt, "context": context, **kwargs})


async def vetka_arc_concepts(text: str) -> Dict[str, Any]:
    """Direct function call for concept extraction."""
    tool = get_arc_concepts_tool()
    return await tool.execute({"text": text})


def register_arc_tools(server) -> None:
    """Register ARC tools with MCP server."""
    gap_tool = get_arc_gap_tool()
    concepts_tool = get_arc_concepts_tool()

    if hasattr(server, 'register_tool'):
        server.register_tool(gap_tool.name, gap_tool)
        server.register_tool(concepts_tool.name, concepts_tool)
        logger.info("ARC tools registered with MCP server")
