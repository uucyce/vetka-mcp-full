"""
VETKA LearnerAgent - Phase 29 Self-Learning
Analyzes failures and suggests improvements

@file learner_agent.py
@status ACTIVE
@phase Phase 60.1 - LangGraph Foundation (Phase 29 Self-Learning)
@calledBy langgraph_nodes.py (learner_node)
@lastAudit 2026-01-10

The LearnerAgent is THE HEART of Phase 29 Self-Learning!

Responsibilities:
1. Categorize failure (syntax, logic, architecture, incomplete, quality)
2. Identify root cause
3. Find similar past failures for learning
4. Suggest improvements
5. Generate enhanced prompt for retry
6. Store lessons for future learning
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FailureAnalysis:
    """Result of failure analysis."""
    failure_category: str       # syntax, logic, architecture, incomplete, quality
    root_cause: str             # What went wrong
    improvement_suggestion: str  # How to fix
    enhanced_prompt: str        # Improved prompt for retry
    confidence: float           # 0-1 confidence in analysis
    similar_failures: List[Dict]  # Similar past failures


class LearnerAgent:
    """
    Analyzes workflow failures and suggests improvements.

    This is the HEART of Phase 29 Self-Learning!

    The LearnerAgent:
    1. Takes failed output and evaluation feedback
    2. Categorizes the type of failure
    3. Searches memory for similar past failures
    4. Generates an enhanced prompt for the retry
    5. Stores lessons learned for future reference

    Learning Categories:
    - syntax: Code has syntax errors or doesn't compile
    - logic: Code compiles but produces wrong results
    - architecture: Design/structure issues, needs refactoring
    - incomplete: Missing features or partial implementation
    - quality: Works but doesn't meet quality standards
    """

    FAILURE_CATEGORIES = {
        'syntax': 'Code has syntax errors or doesn\'t compile',
        'logic': 'Code compiles but produces wrong results',
        'architecture': 'Design/structure issues, needs refactoring',
        'incomplete': 'Missing features or partial implementation',
        'quality': 'Works but doesn\'t meet quality standards'
    }

    # Keywords for category detection
    CATEGORY_KEYWORDS = {
        'syntax': ['syntax', 'parse', 'compile', 'error', 'undefined', 'unexpected token', 'invalid'],
        'logic': ['wrong', 'incorrect', 'bug', 'fail', 'test failed', 'expected', 'actual', 'mismatch'],
        'architecture': ['structure', 'design', 'refactor', 'architecture', 'coupling', 'dependency', 'pattern'],
        'incomplete': ['missing', 'incomplete', 'partial', 'todo', 'not implemented', 'stub', 'placeholder'],
        'quality': ['quality', 'readability', 'maintainability', 'documentation', 'style', 'convention']
    }

    def __init__(
        self,
        memory_manager=None,
        model: str = "qwen2:7b"  # Fast local model for analysis
    ):
        """
        Initialize LearnerAgent.

        Args:
            memory_manager: VETKA MemoryManager for storing lessons
            model: LLM model for deeper analysis (optional)
        """
        self.memory = memory_manager
        self.model = model
        logger.info("[LearnerAgent] Initialized")

    async def analyze_failure(
        self,
        task: str,
        output: str,
        eval_feedback: str,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Analyze why the output failed and suggest improvements.

        Args:
            task: Original task description
            output: Dev agent output that failed
            eval_feedback: Feedback from EvalAgent
            retry_count: Current retry attempt (0-based)

        Returns:
            Dict with:
            - failure_category: Category of failure
            - root_cause: Identified root cause
            - improvement_suggestion: Specific suggestions
            - enhanced_prompt: Improved prompt for retry
            - confidence: Confidence score (0-1)
            - similar_failures: Related past failures
        """
        logger.info(f"[LearnerAgent] 🔍 Analyzing failure (attempt {retry_count + 1})")

        # 1. Categorize failure
        category = await self._categorize_failure(eval_feedback, output)
        logger.debug(f"[LearnerAgent] Category: {category}")

        # 2. Find root cause
        root_cause = await self._find_root_cause(task, output, eval_feedback, category)
        logger.debug(f"[LearnerAgent] Root cause: {root_cause[:100]}...")

        # 3. Find similar past failures
        similar_failures = await self._find_similar_failures(task, category)
        logger.debug(f"[LearnerAgent] Found {len(similar_failures)} similar failures")

        # 4. Generate improvement suggestion
        suggestion = await self._generate_suggestion(
            task, output, eval_feedback, category, root_cause, similar_failures
        )
        logger.debug(f"[LearnerAgent] Suggestion: {suggestion[:100]}...")

        # 5. Create enhanced prompt
        enhanced_prompt = await self._create_enhanced_prompt(
            task, eval_feedback, suggestion, retry_count, similar_failures
        )

        # 6. Store this failure for future learning
        await self._store_failure(
            task, output, eval_feedback, category, root_cause, suggestion
        )

        analysis = {
            'failure_category': category,
            'root_cause': root_cause,
            'improvement_suggestion': suggestion,
            'enhanced_prompt': enhanced_prompt,
            'confidence': self._calculate_confidence(category, similar_failures),
            'similar_failures': similar_failures[:3]  # Top 3
        }

        logger.info(f"[LearnerAgent] 📊 Analysis complete: {category}, confidence: {analysis['confidence']:.2f}")

        return analysis

    async def _categorize_failure(self, feedback: str, output: str) -> str:
        """
        Categorize the type of failure.

        Uses keyword matching for efficiency. Can be enhanced with LLM later.

        Args:
            feedback: EvalAgent feedback
            output: Failed output

        Returns:
            Category string (syntax, logic, architecture, incomplete, quality)
        """
        feedback_lower = feedback.lower()
        output_lower = output.lower()
        combined = f"{feedback_lower} {output_lower}"

        # Score each category by keyword matches
        scores = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in combined)
            scores[category] = score

        # Return highest scoring category, default to 'quality'
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)

        return 'quality'

    async def _find_root_cause(
        self,
        task: str,
        output: str,
        feedback: str,
        category: str
    ) -> str:
        """
        Identify the root cause of failure.

        Args:
            task: Original task
            output: Failed output
            feedback: EvalAgent feedback
            category: Failure category

        Returns:
            Root cause description
        """
        # Build root cause based on category and feedback
        category_context = self.FAILURE_CATEGORIES.get(category, 'Unknown issue')

        # Extract key issues from feedback
        root_cause = f"Category: {category} - {category_context}\n\n"
        root_cause += f"EvalAgent identified: {feedback[:500]}"

        # Category-specific analysis
        if category == 'syntax':
            # Look for error patterns in output
            error_lines = [line for line in output.split('\n') if 'error' in line.lower()]
            if error_lines:
                root_cause += f"\n\nError details:\n" + "\n".join(error_lines[:5])

        elif category == 'logic':
            # Look for test failure patterns
            test_lines = [line for line in output.split('\n') if 'fail' in line.lower() or 'expected' in line.lower()]
            if test_lines:
                root_cause += f"\n\nTest failures:\n" + "\n".join(test_lines[:5])

        elif category == 'incomplete':
            # Look for TODO or unimplemented markers
            todo_lines = [line for line in output.split('\n') if 'todo' in line.lower() or 'not implemented' in line.lower()]
            if todo_lines:
                root_cause += f"\n\nIncomplete sections:\n" + "\n".join(todo_lines[:5])

        return root_cause

    async def _find_similar_failures(
        self,
        task: str,
        category: str
    ) -> List[Dict]:
        """
        Find similar past failures for learning.

        Args:
            task: Current task description
            category: Failure category

        Returns:
            List of similar past failures
        """
        if not self.memory:
            return []

        try:
            # Search for past failures in memory
            results = self.memory.get_similar_context(
                query=f"{category} failure: {task[:200]}",
                limit=5
            )

            # Filter for failure-type entries
            failures = [
                r for r in results
                if r.get('type') in ['lesson_learned', 'failure_analysis', 'workflow_failure']
            ]

            return failures

        except Exception as e:
            logger.warning(f"[LearnerAgent] Could not find similar failures: {e}")
            return []

    async def _generate_suggestion(
        self,
        task: str,
        output: str,
        feedback: str,
        category: str,
        root_cause: str,
        similar_failures: List[Dict]
    ) -> str:
        """
        Generate improvement suggestion.

        Args:
            task: Original task
            output: Failed output
            feedback: EvalAgent feedback
            category: Failure category
            root_cause: Identified root cause
            similar_failures: Past similar failures

        Returns:
            Improvement suggestion string
        """
        # Base suggestions by category
        category_suggestions = {
            'syntax': """
Fix syntax errors and ensure code compiles:
1. Check for missing brackets, parentheses, and quotes
2. Verify proper indentation (especially in Python)
3. Check all imports are correct
4. Run a linter or compiler check before submitting
""",
            'logic': """
Review the algorithm logic and verify correctness:
1. Add unit tests for edge cases
2. Trace through the code with sample inputs
3. Verify loop conditions and boundary checks
4. Check data type conversions
""",
            'architecture': """
Reconsider the design and structure:
1. Break large functions into smaller, focused ones
2. Follow SOLID principles
3. Reduce coupling between components
4. Use appropriate design patterns
""",
            'incomplete': """
Complete all required features:
1. Review the requirements carefully
2. Don't leave TODOs or placeholders
3. Implement all edge cases
4. Add proper error handling
""",
            'quality': """
Improve code quality and maintainability:
1. Add meaningful comments and documentation
2. Use descriptive variable names
3. Follow coding conventions
4. Add input validation
"""
        }

        suggestion = category_suggestions.get(category, "Review and improve the implementation.")

        # Add learnings from similar failures
        if similar_failures:
            suggestion += "\n\n### Past learnings from similar failures:\n"
            for i, failure in enumerate(similar_failures[:2], 1):
                past_suggestion = failure.get('suggestion', failure.get('improvement_suggestion', ''))
                if past_suggestion:
                    suggestion += f"{i}. {past_suggestion[:200]}\n"

        # Add specific feedback from EvalAgent
        suggestion += f"\n\n### Specific issues from evaluation:\n{feedback[:500]}"

        return suggestion

    async def _create_enhanced_prompt(
        self,
        task: str,
        feedback: str,
        suggestion: str,
        retry_count: int,
        similar_failures: List[Dict]
    ) -> str:
        """
        Create enhanced prompt for retry.

        This prompt is added to the context for the next Dev+QA attempt.

        Args:
            task: Original task
            feedback: EvalAgent feedback
            suggestion: Generated suggestion
            retry_count: Current retry attempt
            similar_failures: Past failures for context

        Returns:
            Enhanced prompt string
        """
        enhanced = f"""
## ⚠️ RETRY ATTEMPT {retry_count + 1}

The previous attempt did not meet quality standards. Please address the following issues:

### Previous Feedback (MUST ADDRESS):
{feedback}

### Improvement Guidance:
{suggestion}

### Key Points:
1. This is a retry - the previous attempt had issues
2. Focus specifically on the feedback above
3. Double-check your work before submitting
4. If something is unclear, err on the side of completeness
"""

        # Add past success patterns if available
        if similar_failures:
            enhanced += "\n### Past Successful Approaches:\n"
            for failure in similar_failures[:2]:
                if failure.get('final_score', 0) >= 0.75:
                    approach = failure.get('successful_approach', '')[:200]
                    if approach:
                        enhanced += f"- {approach}\n"

        return enhanced

    async def _store_failure(
        self,
        task: str,
        output: str,
        feedback: str,
        category: str,
        root_cause: str,
        suggestion: str
    ) -> None:
        """
        Store failure for future learning.

        Args:
            task: Original task
            output: Failed output
            feedback: EvalAgent feedback
            category: Failure category
            root_cause: Identified root cause
            suggestion: Generated suggestion
        """
        if not self.memory:
            return

        try:
            failure_data = {
                'type': 'failure_analysis',
                'task': task[:500],
                'output_preview': output[:500],
                'feedback': feedback,
                'category': category,
                'root_cause': root_cause[:500],
                'suggestion': suggestion[:500],
                'timestamp': datetime.now().isoformat(),
                'speaker': 'learner_agent'
            }

            self.memory.triple_write(failure_data)
            logger.debug("[LearnerAgent] 💾 Failure stored for future learning")

        except Exception as e:
            logger.warning(f"[LearnerAgent] Could not store failure: {e}")

    def _calculate_confidence(
        self,
        category: str,
        similar_failures: List[Dict]
    ) -> float:
        """
        Calculate confidence in the analysis.

        Higher confidence if:
        - Clear category match
        - Similar past failures found
        - Past failures have successful resolutions

        Returns:
            Confidence score 0-1
        """
        base_confidence = 0.6

        # Boost for clear category
        if category in ['syntax', 'incomplete']:
            base_confidence += 0.1  # These are usually clear-cut

        # Boost for similar failures found
        if similar_failures:
            base_confidence += min(0.2, len(similar_failures) * 0.05)

            # Extra boost if past failures were resolved
            resolved = sum(1 for f in similar_failures if f.get('final_score', 0) >= 0.75)
            if resolved > 0:
                base_confidence += 0.1

        return min(0.95, base_confidence)

    async def extract_lessons(self, workflow_id: str) -> List[Dict]:
        """
        Extract reusable lessons from a completed workflow.

        Called after successful completion to store what was learned.

        Args:
            workflow_id: Completed workflow ID

        Returns:
            List of extracted lessons
        """
        if not self.memory:
            return []

        try:
            # Get workflow history
            history = self.memory.get_workflow_history(workflow_id)

            lessons = []
            for entry in history:
                retry_count = entry.get('retry_count', entry.get('retries', 0))
                if retry_count > 0:
                    lessons.append({
                        'task_type': entry.get('task_type', entry.get('type', 'unknown')),
                        'initial_failure': entry.get('initial_feedback', entry.get('feedback', ''))[:200],
                        'successful_approach': entry.get('final_output', entry.get('output', ''))[:500],
                        'retries_needed': retry_count,
                        'final_score': entry.get('score', entry.get('final_score', 0))
                    })

            logger.info(f"[LearnerAgent] Extracted {len(lessons)} lessons from workflow {workflow_id}")
            return lessons

        except Exception as e:
            logger.warning(f"[LearnerAgent] Could not extract lessons: {e}")
            return []


# ============ FACTORY FUNCTION ============

def create_learner_agent(memory_manager=None, model: str = "qwen2:7b") -> LearnerAgent:
    """
    Factory function to create LearnerAgent.

    Args:
        memory_manager: VETKA MemoryManager instance
        model: LLM model for analysis

    Returns:
        LearnerAgent instance
    """
    return LearnerAgent(memory_manager=memory_manager, model=model)
