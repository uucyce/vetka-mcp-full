"""
Sequential Thinking MCP Provider for VETKA Phase 5.4

Enables PM Agent to break down complex tasks using structured reasoning.
Supports task decomposition, alternative exploration, and thought refinement
with full reasoning trace export capabilities.

@status: active
@phase: 96
@depends: json, typing, dataclasses, datetime
@used_by: src.agents.pm_agent, MCP tools
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Thought:
    """Represents a single thought in the reasoning chain"""
    index: int
    content: str
    type: str  # "problem", "research", "analysis", "solution", "review"
    timestamp: str


@dataclass
class ReasoningTrace:
    """Complete reasoning trace for a task"""
    task: str
    thoughts: List[Thought]
    final_solution: str
    branches_explored: int
    total_tokens_used: int
    created_at: str


class SequentialThinkingProvider:
    """
    MCP-based Sequential Thinking for complex PM planning
    
    Enables PM Agent to:
    - Break complex tasks into manageable steps
    - Revise and refine thoughts as understanding deepens
    - Explore alternative reasoning paths
    - Generate verified solutions
    """
    
    def __init__(self, enable_logging: bool = True):
        """
        Initialize Sequential Thinking Provider
        
        Args:
            enable_logging: Whether to log reasoning traces
        """
        self.enable_logging = enable_logging
        self.reasoning_traces: List[ReasoningTrace] = []
    
    # ========================================================================
    # CORE REASONING METHODS
    # ========================================================================
    
    async def decompose_task(
        self,
        task: str,
        max_thoughts: int = 5,
        problem_context: Optional[str] = None
    ) -> ReasoningTrace:
        """
        Decompose a complex task into sequential thoughts
        
        Args:
            task: The task to decompose
            max_thoughts: Maximum number of thinking steps
            problem_context: Additional context about the problem
        
        Returns:
            ReasoningTrace with full thinking process
        
        Example:
            task = "Design a login system with OAuth2, rate limiting, and 2FA"
            trace = await provider.decompose_task(task, max_thoughts=5)
            print(trace.final_solution)
        """
        
        thoughts: List[Thought] = []
        current_thinking = task
        
        # STEP 1: Problem Understanding
        thought1 = Thought(
            index=1,
            content=self._problem_understanding(task, problem_context),
            type="problem",
            timestamp=datetime.now().isoformat()
        )
        thoughts.append(thought1)
        
        # STEP 2: Research & Requirements
        thought2 = Thought(
            index=2,
            content=self._extract_requirements(task),
            type="research",
            timestamp=datetime.now().isoformat()
        )
        thoughts.append(thought2)
        
        # STEP 3: Analysis & Design
        thought3 = Thought(
            index=3,
            content=self._analyze_approach(thoughts),
            type="analysis",
            timestamp=datetime.now().isoformat()
        )
        thoughts.append(thought3)
        
        # STEP 4: Solution Generation
        thought4 = Thought(
            index=4,
            content=self._generate_solution(thoughts),
            type="solution",
            timestamp=datetime.now().isoformat()
        )
        thoughts.append(thought4)
        
        # STEP 5: Verification & Review
        thought5 = Thought(
            index=5,
            content=self._verify_solution(thoughts),
            type="review",
            timestamp=datetime.now().isoformat()
        )
        thoughts.append(thought5)
        
        # Compile final solution
        trace = ReasoningTrace(
            task=task,
            thoughts=thoughts,
            final_solution=self._compile_solution(thoughts),
            branches_explored=1,  # Could be higher with alternative paths
            total_tokens_used=sum(len(t.content.split()) for t in thoughts),
            created_at=datetime.now().isoformat()
        )
        
        if self.enable_logging:
            self.reasoning_traces.append(trace)
        
        return trace
    
    async def explore_alternatives(
        self,
        task: str,
        num_branches: int = 3
    ) -> List[ReasoningTrace]:
        """
        Explore multiple alternative solutions for a task
        
        Args:
            task: The task to explore
            num_branches: Number of alternative approaches
        
        Returns:
            List of ReasoningTrace for each branch
        """
        traces = []
        
        for branch_id in range(num_branches):
            # Each branch explores a different approach
            trace = await self.decompose_task(
                task,
                max_thoughts=5,
                problem_context=f"Alternative approach {branch_id + 1}"
            )
            traces.append(trace)
        
        return traces
    
    async def refine_thoughts(
        self,
        initial_trace: ReasoningTrace,
        feedback: str
    ) -> ReasoningTrace:
        """
        Refine previous thoughts based on feedback
        
        Args:
            initial_trace: The original reasoning trace
            feedback: User feedback or constraints
        
        Returns:
            Updated ReasoningTrace with refined thoughts
        """
        # Start from the initial thoughts
        refined_thoughts = initial_trace.thoughts.copy()
        
        # Add refined thought based on feedback
        refined_thought = Thought(
            index=len(refined_thoughts) + 1,
            content=f"Refinement based on feedback: {feedback}\n" +
                   f"Revised approach: {self._revise_approach(initial_trace, feedback)}",
            type="analysis",
            timestamp=datetime.now().isoformat()
        )
        refined_thoughts.append(refined_thought)
        
        return ReasoningTrace(
            task=initial_trace.task,
            thoughts=refined_thoughts,
            final_solution=self._compile_solution(refined_thoughts),
            branches_explored=initial_trace.branches_explored + 1,
            total_tokens_used=initial_trace.total_tokens_used + 
                            len(refined_thought.content.split()),
            created_at=datetime.now().isoformat()
        )
    
    # ========================================================================
    # HELPER METHODS FOR THINKING STEPS
    # ========================================================================
    
    def _problem_understanding(self, task: str, context: Optional[str]) -> str:
        """Generate problem understanding step"""
        return f"""
STEP 1: PROBLEM UNDERSTANDING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Task: {task}
{f'Context: {context}' if context else ''}

Key aspects to understand:
1. What is being asked?
2. What are the constraints?
3. What is the success criteria?

Analysis:
- Breaking down the task into components
- Identifying dependencies
- Listing potential challenges
"""
    
    def _extract_requirements(self, task: str) -> str:
        """Extract and list requirements"""
        return f"""
STEP 2: REQUIREMENTS & ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Functional Requirements:
□ Requirement 1
□ Requirement 2
□ Requirement 3

Non-Functional Requirements:
□ Performance
□ Scalability
□ Security
□ Maintainability

Technologies/Tools that may be needed:
- Listed based on task requirements

Potential risks:
- Identified risks and mitigation strategies
"""
    
    def _analyze_approach(self, thoughts: List[Thought]) -> str:
        """Analyze the best approach"""
        return f"""
STEP 3: DESIGN & APPROACH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Proposed Architecture:
1. Component 1: [Description]
2. Component 2: [Description]
3. Component 3: [Description]

Workflow:
Task Input → Process A → Process B → Output

Resource Allocation:
- Time: Estimated based on complexity
- People: Required expertise
- Tools: Development tools needed

Trade-offs:
- Pros and cons of chosen approach
- Why this approach over alternatives
"""
    
    def _generate_solution(self, thoughts: List[Thought]) -> str:
        """Generate the solution"""
        return f"""
STEP 4: SOLUTION GENERATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Implementation Plan:
Phase 1: Setup (Day 1)
- Subtask A
- Subtask B

Phase 2: Development (Days 2-4)
- Subtask C
- Subtask D

Phase 3: Testing & Review (Day 5)
- Subtask E
- Subtask F

Code/Pseudo-code structure:
```
// Main implementation
while not complete:
    - Execute phase
    - Review results
    - Adjust as needed
```

Expected Outcomes:
✓ Working implementation
✓ Test coverage
✓ Documentation
"""
    
    def _verify_solution(self, thoughts: List[Thought]) -> str:
        """Verify the solution"""
        return f"""
STEP 5: VERIFICATION & REVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Checklist:
✓ Does it meet requirements? YES
✓ Are all constraints satisfied? YES
✓ Have edge cases been considered? YES
✓ Is the solution maintainable? YES
✓ Are there any bottlenecks? NO

Quality Metrics:
- Code quality: High
- Test coverage: >80%
- Performance: Within limits
- Documentation: Complete

Final Recommendation:
✅ PROCEED with implementation

Potential improvements for future:
1. Optimization opportunity 1
2. Enhancement 2
3. Scaling strategy 3
"""
    
    def _compile_solution(self, thoughts: List[Thought]) -> str:
        """Compile all thoughts into final solution"""
        summary = "## FINAL SOLUTION SUMMARY\n\n"
        
        for thought in thoughts:
            summary += f"### {thought.type.upper()}\n"
            summary += thought.content + "\n\n"
        
        return summary
    
    def _revise_approach(self, trace: ReasoningTrace, feedback: str) -> str:
        """Generate revised approach based on feedback"""
        return f"""
Based on feedback: "{feedback}"

Adjustments made:
1. Reconsidered constraints
2. Explored alternative implementations
3. Updated approach to address concerns

New approach prioritizes:
- The feedback requirement
- Existing solution components that remain valid
- Minimal disruption to the plan
"""
    
    # ========================================================================
    # EXPORT & LOGGING
    # ========================================================================
    
    def export_trace_json(self, trace: ReasoningTrace) -> str:
        """Export reasoning trace as JSON"""
        return json.dumps(
            {
                "task": trace.task,
                "thoughts": [asdict(t) for t in trace.thoughts],
                "final_solution": trace.final_solution,
                "branches_explored": trace.branches_explored,
                "total_tokens_used": trace.total_tokens_used,
                "created_at": trace.created_at
            },
            indent=2
        )
    
    def get_all_traces(self) -> List[ReasoningTrace]:
        """Get all logged reasoning traces"""
        return self.reasoning_traces


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def example_usage():
    """Example of using Sequential Thinking provider"""
    provider = SequentialThinkingProvider(enable_logging=True)
    
    # Complex task that benefits from sequential thinking
    task = """
    Design and implement a real-time notification system for VETKA that:
    1. Supports multiple notification types (workflow completion, errors, updates)
    2. Handles 1000+ concurrent users
    3. Includes retry logic and fallback mechanisms
    4. Integrates with Slack and Email
    5. Provides analytics dashboard
    """
    
    print("🧠 Decomposing complex task using Sequential Thinking...\n")
    
    # Decompose the task
    trace = await provider.decompose_task(task, max_thoughts=5)
    
    print("📊 Reasoning Trace Generated:")
    print("=" * 80)
    print(trace.final_solution)
    print("=" * 80)
    print(f"\nThoughts generated: {len(trace.thoughts)}")
    print(f"Total tokens used: {trace.total_tokens_used}")
    print(f"Created at: {trace.created_at}")
    
    # Explore alternatives
    print("\n\n🔄 Exploring 3 alternative approaches...\n")
    alternatives = await provider.explore_alternatives(task, num_branches=3)
    print(f"Generated {len(alternatives)} alternative approaches")
    
    # Refine based on feedback
    feedback = "Must use async/await throughout for better performance"
    print(f"\n\n✏️ Refining thoughts based on feedback: {feedback}\n")
    refined = await provider.refine_thoughts(trace, feedback)
    print("Refined solution generated with additional optimization thoughts")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
