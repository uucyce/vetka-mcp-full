"""
VETKA Phase 99.3 - ARC Gap Detector

Detects conceptual gaps before agent calls using semantic search and ARC methodology.
Implements TODO_ARC_GAP from orchestrator_with_elisya.py:2328.

Pipeline:
1. Extract key concepts from prompt/context
2. Semantic search for related concepts in Qdrant
3. Compare with ARC few-shot examples
4. Identify missing connections/patterns
5. Format suggestions for prompt injection

@status: active
@phase: 99.3
@depends: re, logging, typing
@used_by: orchestrator_with_elisya.py (run_single_agent_async)
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ConceptGap:
    """Represents a detected conceptual gap."""
    concept: str
    related_concepts: List[str]
    gap_type: str  # 'missing_connection', 'missing_pattern', 'missing_context'
    confidence: float  # 0.0 - 1.0
    suggestion: str
    source: str  # 'semantic_search', 'arc_few_shot', 'pattern_match'


@dataclass
class GapDetectionResult:
    """Result of gap detection analysis."""
    gaps: List[ConceptGap] = field(default_factory=list)
    extracted_concepts: List[str] = field(default_factory=list)
    related_found: int = 0
    suggestions_text: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ARCGapDetector:
    """
    Detects conceptual gaps before agent execution.

    Uses lightweight keyword extraction + semantic search
    to find missing connections that could improve agent output.

    FIX_99.3: Implements TODO_ARC_GAP
    """

    # Common programming/VETKA concepts for pattern matching
    CONCEPT_PATTERNS = [
        r'\b(api|endpoint|route|handler)\b',
        r'\b(database|db|qdrant|weaviate|storage)\b',
        r'\b(auth|authentication|token|session)\b',
        r'\b(test|testing|pytest|unittest)\b',
        r'\b(config|configuration|settings|env)\b',
        r'\b(cache|memory|buffer|stm|mgc)\b',
        r'\b(workflow|pipeline|orchestrat\w*)\b',
        r'\b(agent|model|llm|gpt|claude|grok)\b',
        r'\b(error|exception|handling|retry)\b',
        r'\b(file|path|directory|folder)\b',
        r'\b(socket|websocket|stream|realtime)\b',
        r'\b(ui|frontend|component|react)\b',
        r'\b(cam|hope|arc|elisya)\b',  # VETKA-specific
    ]

    def __init__(
        self,
        memory_manager: Optional[Any] = None,
        arc_solver: Optional[Any] = None,
        min_confidence: float = 0.3,
        max_suggestions: int = 3
    ):
        """
        Args:
            memory_manager: MemoryManager for semantic search
            arc_solver: ARCSolverAgent for few-shot examples
            min_confidence: Minimum confidence to include a gap
            max_suggestions: Maximum suggestions to return
        """
        self.memory = memory_manager
        self.arc_solver = arc_solver
        self.min_confidence = min_confidence
        self.max_suggestions = max_suggestions

        # Compile patterns
        self._patterns = [re.compile(p, re.IGNORECASE) for p in self.CONCEPT_PATTERNS]

        logger.debug(f"ARCGapDetector initialized: min_conf={min_confidence}, max_sugg={max_suggestions}")

    def extract_concepts(self, text: str) -> List[str]:
        """
        Extract key concepts from text using pattern matching.

        Fast O(n) extraction without LLM calls.

        Args:
            text: Input text (prompt + context)

        Returns:
            List of extracted concept keywords
        """
        if not text:
            return []

        concepts = set()
        text_lower = text.lower()

        # Pattern-based extraction
        for pattern in self._patterns:
            matches = pattern.findall(text_lower)
            concepts.update(matches)

        # Also extract CamelCase and snake_case identifiers
        camel_case = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', text)
        snake_case = re.findall(r'\b[a-z]+(?:_[a-z]+)+\b', text)

        for term in camel_case + snake_case:
            # Normalize to lowercase words
            words = re.findall(r'[A-Z]?[a-z]+', term)
            concepts.update(w.lower() for w in words if len(w) > 2)

        return list(concepts)[:20]  # Limit to top 20

    async def find_related_concepts(
        self,
        concepts: List[str],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find related concepts via semantic search.

        Args:
            concepts: List of extracted concepts
            limit: Max results per concept

        Returns:
            List of related concept dicts with scores
        """
        if not self.memory or not concepts:
            return []

        related = []
        query = " ".join(concepts)

        try:
            # Use memory manager's semantic search
            if hasattr(self.memory, 'search'):
                results = await self.memory.search(query, limit=limit)
                if results:
                    for r in results:
                        related.append({
                            'content': r.get('content', str(r))[:200],
                            'score': r.get('score', 0.5),
                            'path': r.get('path', r.get('file_path', '')),
                            'source': 'qdrant'
                        })
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")

        return related

    def detect_gaps(
        self,
        extracted: List[str],
        related: List[Dict[str, Any]],
        few_shot_examples: List[Dict] = None
    ) -> List[ConceptGap]:
        """
        Detect conceptual gaps by comparing extracted vs related concepts.

        Args:
            extracted: Concepts extracted from prompt
            related: Related concepts from semantic search
            few_shot_examples: ARC few-shot examples (optional)

        Returns:
            List of detected ConceptGaps
        """
        gaps = []
        extracted_set = set(extracted)

        # 1. Find concepts in related that aren't in extracted
        for item in related:
            content = item.get('content', '').lower()
            path = item.get('path', '')
            score = item.get('score', 0.5)

            # Extract concepts from related content
            related_concepts = self.extract_concepts(content)

            # Find new concepts not in original
            new_concepts = [c for c in related_concepts if c not in extracted_set]

            if new_concepts and score >= self.min_confidence:
                gap = ConceptGap(
                    concept=new_concepts[0],
                    related_concepts=new_concepts[:3],
                    gap_type='missing_connection',
                    confidence=score,
                    suggestion=f"Consider: {', '.join(new_concepts[:3])} (from {path})",
                    source='semantic_search'
                )
                gaps.append(gap)

        # 2. Check ARC few-shot examples for patterns
        # FIX_99.3: Use both few_shot extraction AND arc_solver reasoning
        if few_shot_examples:
            for example in few_shot_examples[-5:]:  # Last 5
                example_type = example.get('type', '')
                if example_type in ['connection', 'pattern', 'transformation', 'optimization']:
                    # Check if pattern applies
                    pattern_concepts = self.extract_concepts(
                        example.get('explanation', '') + example.get('code', '')
                    )
                    missing = [c for c in pattern_concepts if c not in extracted_set]

                    if missing:
                        gap = ConceptGap(
                            concept=missing[0],
                            related_concepts=missing[:3],
                            gap_type='missing_pattern',
                            confidence=example.get('score', 0.5),
                            suggestion=f"ARC pattern suggests: {', '.join(missing[:3])}",
                            source='arc_few_shot'
                        )
                        gaps.append(gap)

        # 3. Use ARC Solver for deep reasoning (if available and not too many gaps yet)
        if self.arc_solver and len(gaps) < self.max_suggestions:
            arc_gaps = self._get_arc_solver_suggestions(extracted, extracted_set)
            gaps.extend(arc_gaps)

        # Sort by confidence and limit
        gaps.sort(key=lambda g: g.confidence, reverse=True)
        return gaps[:self.max_suggestions]

    def _get_arc_solver_suggestions(
        self,
        extracted: List[str],
        extracted_set: set
    ) -> List[ConceptGap]:
        """
        Use ARC Solver for deep pattern-based suggestions.

        FIX_99.3: Real integration with ARCSolverAgent.

        Args:
            extracted: Extracted concepts from prompt
            extracted_set: Set of extracted concepts for quick lookup

        Returns:
            List of ConceptGaps from ARC analysis
        """
        gaps = []

        if not self.arc_solver:
            return gaps

        try:
            # Use ARC Solver's suggest_connections for deep analysis
            if hasattr(self.arc_solver, 'suggest_connections'):
                # Build minimal graph context from concepts
                task_context = f"Analyzing concepts: {', '.join(extracted[:10])}"

                arc_result = self.arc_solver.suggest_connections(
                    workflow_id="gap_detection",
                    graph_data=None,  # No graph, just concept analysis
                    task_context=task_context,
                    num_candidates=3,  # Keep it fast
                    min_score=self.min_confidence
                )

                # Convert ARC suggestions to ConceptGaps
                for sugg in arc_result.get('top_suggestions', []):
                    sugg_type = sugg.get('type', 'transformation')
                    explanation = sugg.get('explanation', '')
                    score = sugg.get('score', 0.5)

                    # Extract concepts from ARC suggestion
                    sugg_concepts = self.extract_concepts(explanation)
                    new_concepts = [c for c in sugg_concepts if c not in extracted_set]

                    if new_concepts and score >= self.min_confidence:
                        gap = ConceptGap(
                            concept=new_concepts[0],
                            related_concepts=new_concepts[:3],
                            gap_type='arc_reasoning',
                            confidence=score,
                            suggestion=f"ARC suggests: {explanation[:100]}",
                            source='arc_solver'
                        )
                        gaps.append(gap)

                logger.debug(f"ARC Solver returned {len(gaps)} suggestions")

            # Also check few_shot_examples directly from ARC Solver
            elif hasattr(self.arc_solver, 'few_shot_examples'):
                for example in self.arc_solver.few_shot_examples[-3:]:
                    example_dict = example.to_dict() if hasattr(example, 'to_dict') else example
                    explanation = example_dict.get('explanation', '')
                    score = example_dict.get('score', 0.5)

                    sugg_concepts = self.extract_concepts(explanation)
                    new_concepts = [c for c in sugg_concepts if c not in extracted_set]

                    if new_concepts and score >= self.min_confidence:
                        gap = ConceptGap(
                            concept=new_concepts[0],
                            related_concepts=new_concepts[:3],
                            gap_type='arc_few_shot',
                            confidence=score,
                            suggestion=f"ARC learned: {explanation[:80]}",
                            source='arc_solver_cache'
                        )
                        gaps.append(gap)

        except Exception as e:
            logger.warning(f"ARC Solver integration failed: {e}")

        return gaps

    def format_suggestions(self, gaps: List[ConceptGap]) -> str:
        """
        Format gap suggestions for prompt injection.

        Args:
            gaps: Detected conceptual gaps

        Returns:
            Formatted string for prompt injection
        """
        if not gaps:
            return ""

        lines = ["\n[ARC Gap Analysis - Consider these related concepts:]"]

        for i, gap in enumerate(gaps, 1):
            confidence_stars = "★" * int(gap.confidence * 5)
            lines.append(
                f"{i}. {gap.suggestion} ({confidence_stars})"
            )

        lines.append("")  # Empty line at end
        return "\n".join(lines)

    async def analyze(
        self,
        prompt: str,
        context: str = ""
    ) -> GapDetectionResult:
        """
        Main entry point: analyze prompt/context for conceptual gaps.

        FIX_99.3: Called from orchestrator before agent execution.

        Args:
            prompt: User prompt/request
            context: Additional context (raw_context, etc.)

        Returns:
            GapDetectionResult with gaps and suggestions
        """
        try:
            # Combine prompt and context
            full_text = f"{prompt}\n{context}"

            # 1. Extract concepts
            concepts = self.extract_concepts(full_text)
            logger.debug(f"Extracted {len(concepts)} concepts: {concepts[:5]}...")

            # 2. Find related via semantic search
            related = await self.find_related_concepts(concepts)
            logger.debug(f"Found {len(related)} related items")

            # 3. Get ARC few-shot examples if available
            few_shots = []
            if self.arc_solver and hasattr(self.arc_solver, 'few_shot_examples'):
                few_shots = [e.to_dict() if hasattr(e, 'to_dict') else e
                            for e in self.arc_solver.few_shot_examples]

            # 4. Detect gaps
            gaps = self.detect_gaps(concepts, related, few_shots)
            logger.info(f"Detected {len(gaps)} conceptual gaps")

            # 5. Format suggestions
            suggestions_text = self.format_suggestions(gaps)

            return GapDetectionResult(
                gaps=gaps,
                extracted_concepts=concepts,
                related_found=len(related),
                suggestions_text=suggestions_text
            )

        except Exception as e:
            logger.error(f"Gap detection failed: {e}")
            return GapDetectionResult()


# === Convenience functions ===

_detector_instance: Optional[ARCGapDetector] = None


def get_gap_detector(
    memory_manager: Optional[Any] = None,
    arc_solver: Optional[Any] = None
) -> ARCGapDetector:
    """Get or create singleton gap detector."""
    global _detector_instance

    if _detector_instance is None:
        _detector_instance = ARCGapDetector(
            memory_manager=memory_manager,
            arc_solver=arc_solver
        )
    elif memory_manager and not _detector_instance.memory:
        _detector_instance.memory = memory_manager
    elif arc_solver and not _detector_instance.arc_solver:
        _detector_instance.arc_solver = arc_solver

    return _detector_instance


async def detect_conceptual_gaps(
    prompt: str,
    context: str = "",
    memory_manager: Optional[Any] = None,
    arc_solver: Optional[Any] = None
) -> str:
    """
    Convenience function for gap detection.

    FIX_99.3: Direct replacement for TODO_ARC_GAP.

    Args:
        prompt: User prompt
        context: Additional context
        memory_manager: Optional memory manager
        arc_solver: Optional ARC solver agent

    Returns:
        Formatted suggestions string (empty if no gaps)
    """
    detector = get_gap_detector(memory_manager, arc_solver)
    result = await detector.analyze(prompt, context)
    return result.suggestions_text


def reset_gap_detector() -> None:
    """Reset singleton (for testing)."""
    global _detector_instance
    _detector_instance = None
