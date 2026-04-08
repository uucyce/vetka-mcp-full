"""
EvalAgent - Self-reflective output evaluation with scoring and feedback loop + LOD

@file eval_agent.py
@status ACTIVE (Phase 34)
@calledBy orchestrator_with_elisya.py (_evaluate_with_eval_agent)
@when After MERGE step, before OPS
@action Quality gate - evaluates workflow output
@lastAudit 2026-01-04
"""

import ollama  # Switched from httpx to ollama SDK
import json
import re
from typing import Tuple, Dict, Any, List
from pathlib import Path
from datetime import datetime


class EvalAgent:
    """
    Оценивает output агентов по 4 критериям:
    - Correctness (40%): соответствие требованиям
    - Completeness (30%): полнота покрытия
    - Code Quality (20%): чистота, структура (только для кода)
    - Clarity (10%): понятность для пользователя
    
    Использует Ollama + local LLM (Llama 3.1 или Deepseek)
    Интегрирован с Weaviate для feedback хранения
    
    Phase 7 NEW: LOD (Level of Detail) по сложности + Few-shot learning
    ✅ Phase 7.1: Ollama SDK вместо httpx + MemoryManager integration
    """
    
    def __init__(self, model: str = "deepseek-coder:6.7b", max_retries: int = 3, memory_manager=None):
        self.ollama_base_url = "http://localhost:11434"
        self.model = model
        self.max_retries = max_retries
        self.evaluation_history = []
        self.memory_manager = memory_manager  # ✅ NEW: MemoryManager для сохранения high-scores
    
    def _get_token_budget(self, complexity: str) -> int:
        """
        LOD (Level of Detail) по сложности — Phase 7 optimization
        Адаптивный token budget для EvalAgent
        Меньше токенов для простых задач → быстрее
        Больше токенов для сложных → точнее
        """
        budget_map = {
            'MICRO': 500,      # Простые задачи: быстрая оценка
            'SMALL': 1500,     # Маленькие задачи: стандартная оценка
            'MEDIUM': 3000,    # Средние задачи: полная оценка (default)
            'LARGE': 6000,     # Большие задачи: детальная оценка
            'EPIC': 12000,     # Эпические задачи: очень детальная оценка
        }
        return budget_map.get(complexity.upper(), 3000)
    
    def _get_eval_depth(self, complexity: str) -> str:
        """LOD: глубина анализа по сложности"""
        depth_map = {
            'MICRO': "quick",      # Только основные критерии
            'SMALL': "standard",   # Все 4 критерия
            'MEDIUM': "standard",  # Все 4 критерия
            'LARGE': "deep",       # Все 4 + примеры + рекомендации
            'EPIC': "thorough",    # Все 4 + примеры + рекомендации + edge cases
        }
        return depth_map.get(complexity.upper(), "standard")
    
    def evaluate(
        self,
        task: str = "",  # Phase 27.11: Made optional for kwargs-only calls
        output: str = "",  # Phase 27.11: Made optional for kwargs-only calls
        complexity: str = "MEDIUM",
        reference: str = None,
        ground_truth: str = None,
        few_shot_examples: List[str] = None,
        original_task: str = None,  # Phase 27.11: Alias for task
        agent_output: str = None,  # Phase 27.11: Alias for output
        agent_name: str = None,  # Phase 27.11: Ignored but accepted
        **kwargs  # Phase 27.11: Catch-all for other unexpected args
    ) -> Dict[str, Any]:
        """
        Основной метод оценки с LOD адаптацией

        Args:
            task: Описание задачи
            output: Output который нужно оценить
            complexity: MICRO/SMALL/MEDIUM/LARGE/EPIC
            reference: Опциональный reference output (для сравнения)
            ground_truth: Опциональная ground truth (для RAG)
            few_shot_examples: Few-shot примеры из Weaviate (для LARGE/EPIC)
            original_task: Alias for task (orchestrator compatibility)
            agent_output: Alias for output (orchestrator compatibility)
            agent_name: Agent identifier (ignored, for logging only)
            kwargs: Additional unexpected arguments (ignored)

        Returns:
            {
                "score": 0.75,
                "correctness": 0.8,
                "completeness": 0.7,
                "code_quality": 0.7,
                "clarity": 0.8,
                "feedback": "Good overall, but missing edge cases",
                "should_retry": False,
                "retry_reason": None,
                "evaluation_id": "eval_123",
                "token_budget": 3000,
                "eval_depth": "standard"
            }
        """
        # Phase 27.11: Handle aliases for compatibility
        if not task and original_task:
            task = original_task
        if not output and agent_output:
            output = agent_output
        # Fallback defaults if still empty
        if not task:
            task = "No task provided"
        if not output:
            output = "No output provided"
        
        eval_id = f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        token_budget = self._get_token_budget(complexity)
        eval_depth = self._get_eval_depth(complexity)
        
        # Build evaluation prompt with LOD
        prompt = self._build_eval_prompt(
            task, output, complexity, reference, ground_truth,
            few_shot_examples=few_shot_examples,
            token_budget=token_budget,
            eval_depth=eval_depth
        )
        
        # Call LLM for evaluation
        try:
            response = self._call_llm(prompt)
            scores = self._parse_eval_response(response)
        except Exception as e:
            return {
                "score": 0.5,
                "error": str(e),
                "evaluation_id": eval_id,
                "status": "error",
                "token_budget": token_budget,
                "eval_depth": eval_depth,
            }
        
        # Calculate weighted total score
        total_score = (
            scores.get("correctness", 0.5) * 0.4 +
            scores.get("completeness", 0.5) * 0.3 +
            scores.get("code_quality", 0.5) * 0.2 +
            scores.get("clarity", 0.5) * 0.1
        )
        
        result = {
            "evaluation_id": eval_id,
            "task": task,
            "complexity": complexity,
            "score": round(total_score, 2),
            "scores": {
                "correctness": round(scores.get("correctness", 0.5), 2),
                "completeness": round(scores.get("completeness", 0.5), 2),
                "code_quality": round(scores.get("code_quality", 0.5), 2),
                "clarity": round(scores.get("clarity", 0.5), 2),
            },
            "feedback": scores.get("feedback", "Evaluation complete"),
            "should_retry": total_score < 0.7,
            "status": "success",
            "token_budget": token_budget,
            "eval_depth": eval_depth,
        }
        
        # Store in history
        self.evaluation_history.append(result)

        # ✅ Phase 8.0: Citation extraction (RAG support)
        citations = self._extract_citations_from_output(output)
        if citations:
            result['citations'] = citations
            result['has_citations'] = True

        # ✅ NEW: Save high-scores to Weaviate via MemoryManager
        if result.get("score", 0) >= 0.8 and self.memory_manager:
            self.save_high_score_to_weaviate(task, output, result)

        return result
    
    def evaluate_with_retry(
        self,
        task: str,
        output: str,
        complexity: str = "MEDIUM",
        few_shot_examples: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Оценка с автоматическим retry (max 3 раза)
        Каждый retry меняет prompt для улучшения
        
        Phase 7: Retry 2 использует few-shot examples из Weaviate
        
        Returns: Final result after all retries
        """
        
        retry_count = 0
        current_output = output
        
        while retry_count < self.max_retries:
            result = self.evaluate(
                task=task,
                output=current_output,
                complexity=complexity,
                few_shot_examples=few_shot_examples if retry_count == 2 else None,
            )
            
            result["retry_count"] = retry_count
            
            # If score >= 0.7, stop retrying
            if result.get("score", 0) >= 0.7:
                result["final_status"] = "success"
                return result
            
            retry_count += 1
            
            # If last retry, escalate to user
            if retry_count >= self.max_retries:
                result["final_status"] = "escalate_to_user"
                result["message"] = f"Score remained below 0.7 after {self.max_retries} retries. Please review manually."
                return result
            
            # Modify prompt for next retry (progressive disclosure)
            if retry_count == 1:
                current_output = self._enhance_with_specificity(
                    task, current_output, result
                )
            elif retry_count == 2:
                current_output = self._enhance_with_chain_of_thought(
                    task, current_output, result
                )
        
        return result
    
    def _build_eval_prompt(
        self,
        task: str,
        output: str,
        complexity: str,
        reference: str = None,
        ground_truth: str = None,
        few_shot_examples: List[str] = None,
        token_budget: int = 3000,
        eval_depth: str = "standard",
    ) -> str:
        """
        Построить eval prompt с критериями + LOD адаптацией
        Phase 7: Few-shot примеры + depth-adaptive criteria
        """
        
        prompt = f"""EVALUATION TASK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Complexity: {complexity}
Eval Depth: {eval_depth}
Token Budget: {token_budget}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Original Task:
{task}

Output to Evaluate:
{output}

"""
        
        if reference:
            prompt += f"""Reference Output:
{reference}

"""
        
        if ground_truth:
            prompt += f"""Ground Truth / Rubric:
{ground_truth}

"""
        
        # Few-shot examples для LARGE/EPIC (Phase 7)
        if few_shot_examples and eval_depth in ["deep", "thorough"]:
            prompt += """REFERENCE EXAMPLES (High-Score):
"""
            for i, example in enumerate(few_shot_examples[:3]):  # Max 3 examples
                prompt += f"""
Example {i+1}:
{example}

"""
        
        # Criteria по depth
        if eval_depth == "quick":
            prompt += """QUICK EVALUATION (fast path for simple tasks):

Score ONLY Correctness (1.0 = 100% correct, 0.0 = completely wrong):

RESPOND ONLY IN THIS JSON FORMAT:
{
  "correctness": 0.8,
  "completeness": 0.8,
  "code_quality": 0.8,
  "clarity": 0.8,
  "feedback": "Brief feedback"
}
"""
        elif eval_depth == "standard":
            prompt += """SCORE EACH CRITERION (0-1 scale):

1. CORRECTNESS (40%):
   - Does the output correctly address the task?
   - Are there factual errors or logical flaws?
   - Score: [0-1]

2. COMPLETENESS (30%):
   - Does it cover all required elements?
   - Are there missing parts?
   - Score: [0-1]

3. CODE QUALITY (20%): [if applicable]
   - Is code clean and well-structured?
   - Follows best practices?
   - No syntax errors?
   - Score: [0-1]

4. CLARITY (10%):
   - Is it easy to understand?
   - Well-organized and readable?
   - Score: [0-1]

RESPOND ONLY IN THIS JSON FORMAT:
{
  "correctness": 0.8,
  "completeness": 0.7,
  "code_quality": 0.75,
  "clarity": 0.85,
  "feedback": "Brief feedback on strengths and weaknesses"
}
"""
        else:  # deep or thorough
            prompt += """DETAILED EVALUATION (all criteria + recommendations):

1. CORRECTNESS (40%):
   - Does it correctly address the task?
   - Factual accuracy? Logical validity?
   - Compare with reference examples if provided
   - Score: [0-1]

2. COMPLETENESS (30%):
   - All required elements included?
   - Edge cases covered?
   - Score: [0-1]

3. CODE QUALITY (20%):
   - Code structure and cleanliness?
   - Best practices followed?
   - Maintainability?
   - Score: [0-1]

4. CLARITY (10%):
   - Easy to understand?
   - Well-documented?
   - Clear variable names?
   - Score: [0-1]

RECOMMENDATIONS (if depth is thorough):
- List 2-3 specific improvements
- Highlight strengths
- Suggest edge cases to handle

RESPOND ONLY IN THIS JSON FORMAT:
{
  "correctness": 0.8,
  "completeness": 0.7,
  "code_quality": 0.75,
  "clarity": 0.85,
  "feedback": "Detailed feedback with improvements",
  "recommendations": ["Improvement 1", "Improvement 2"]
}
"""
        
        prompt += """
STRICT: Must be valid JSON only. No markdown, no explanation.
"""
        
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """
        Call Ollama LLM for evaluation
        ✅ Phase 7.1: Using ollama SDK instead of httpx
        """
        try:
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={
                    "temperature": 0.3,  # Lower temp for consistency
                }
            )
            return response.get("response", "")
        except Exception as e:
            raise Exception(f"Ollama LLM call failed: {str(e)}")
    
    def _parse_eval_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response from LLM"""
        
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                return data
            else:
                # Fallback: try parsing entire response
                data = json.loads(response)
                return data
        except json.JSONDecodeError:
            # If JSON parsing fails, return default scores
            return {
                "correctness": 0.5,
                "completeness": 0.5,
                "code_quality": 0.5,
                "clarity": 0.5,
                "feedback": "Could not parse evaluation"
            }
    
    def _enhance_with_specificity(
        self,
        task: str,
        output: str,
        previous_result: Dict[str, Any]
    ) -> str:
        """Retry 1: Add specificity based on weakest criterion"""
        
        scores = previous_result.get("scores", {})
        weakest = min(scores.items(), key=lambda x: x[1])
        
        enhancement = f"\n\n[RETRY 1 - Focus: {weakest[0]}]\nPlease ensure: "
        
        if weakest[0] == "correctness":
            enhancement += "Verify all facts are accurate and match the requirements exactly."
        elif weakest[0] == "completeness":
            enhancement += "Include all required elements and edge cases mentioned in the task."
        elif weakest[0] == "code_quality":
            enhancement += "Follow PEP8 standards, add meaningful comments, avoid code duplication."
        elif weakest[0] == "clarity":
            enhancement += "Make explanations clear and easy to understand for non-technical users."
        
        return output + enhancement
    
    def _enhance_with_chain_of_thought(
        self,
        task: str,
        output: str,
        previous_result: Dict[str, Any]
    ) -> str:
        """Retry 2: Add chain-of-thought reasoning"""
        
        enhancement = f"\n\n[RETRY 2 - Chain-of-Thought]\nStep-by-step reasoning:\n"
        enhancement += "1. What are the exact requirements?\n"
        enhancement += "2. How does the output address each requirement?\n"
        enhancement += "3. What could be improved?\n"
        enhancement += "Please revise with this reasoning in mind."
        
        return output + enhancement
    
    def _extract_citations_from_output(self, output: str) -> List[Dict[str, str]]:
        """
        Extract sources/citations from output (RAG support)
        Phase 8.0: Citation extraction for transparency

        Supports formats:
        - [source:filename.py]
        - [cite:document_name]
        - (source: reference_text)
        - [[1]] style references
        """
        citations = []
        patterns = [
            (r'\[source:([^\]]+)\]', 'source'),
            (r'\[cite:([^\]]+)\]', 'citation'),
            (r'\(source: ([^\)]+)\)', 'reference'),
            (r'\[\[(\d+)\]\]', 'footnote'),
            (r'<ref>([^<]+)</ref>', 'xml_ref'),
        ]

        for pattern, ref_type in patterns:
            matches = re.findall(pattern, output)
            for match in matches:
                citations.append({
                    'source': match.strip(),
                    'type': ref_type
                })

        return citations

    def get_history(self, limit: int = 10) -> list:
        """Get evaluation history"""
        return self.evaluation_history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get evaluation statistics"""
        
        if not self.evaluation_history:
            return {
                "total_evaluations": 0,
                "average_score": 0,
                "success_rate": 0,
            }
        
        total = len(self.evaluation_history)
        successful = sum(1 for e in self.evaluation_history if e.get("score", 0) >= 0.7)
        avg_score = sum(e.get("score", 0) for e in self.evaluation_history) / total
        
        return {
            "total_evaluations": total,
            "average_score": round(avg_score, 2),
            "success_rate": round(successful / total * 100, 1),
            "successful": successful,
            "failed": total - successful,
        }
    
    def save_high_score_to_weaviate(
        self,
        task: str,
        output: str,
        eval_result: Dict[str, Any]
    ) -> bool:
        """
        Save high-score (>0.8) examples to Weaviate via MemoryManager
        for few-shot learning in future tasks (Phase 7.1)
        
        ✅ Now uses MemoryManager instead of direct Weaviate client
        """
        
        if eval_result.get("score", 0) < 0.8:
            return False
        
        if self.memory_manager is None:
            print(f"⚠️  MemoryManager not available, skipping save")
            return False
        
        try:
            # Save via MemoryManager
            self.memory_manager.save_feedback(
                evaluation_id=eval_result['evaluation_id'],
                task=task,
                output=output[:1000],  # Truncate for storage
                rating="high_score_eval",
                score=eval_result['score']
            )
            print(f"✅ Saved high-score example to Weaviate: {task[:50]}... (score: {eval_result['score']})")
            return True
        except Exception as e:
            print(f"❌ Failed to save to Weaviate: {e}")
            return False


def eval_agent_factory(model: str = "deepseek-coder:6.7b", memory_manager=None) -> EvalAgent:
    """Factory for creating EvalAgent instance with optional MemoryManager"""
    return EvalAgent(model=model, memory_manager=memory_manager)
