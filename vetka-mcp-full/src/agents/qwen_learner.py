"""
Qwen2-7B Learner - Fast workflow analyzer via Ollama.

Text-only analysis optimized for speed.
Reliable fallback when Pixtral unavailable.

@file qwen_learner.py
@status: active
@phase: 96
@depends: ollama, .base_learner.BaseLearner, .learner_factory.LearnerFactory
@used_by: src/initialization/dependency_check.py (dynamic loading via LearnerFactory)
"""

import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid
from dataclasses import dataclass, asdict

from .base_learner import BaseLearner
from .learner_factory import LearnerFactory

# Check ollama availability
try:
    import ollama

    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("⚠️  Qwen learner requires: pip install ollama")


@dataclass
class LearningLesson:
    """Structured learning lesson"""

    id: str
    workflow_id: str
    task_description: str
    approach: str
    success_factors: List[str]
    failure_factors: List[str]
    semantic_tags: List[str]
    relationships: List[str]
    score: float
    timestamp: str
    model: str = "qwen2-7b"

    def to_dict(self) -> Dict:
        return asdict(self)


@LearnerFactory.register("qwen")
class QwenLearner(BaseLearner):
    """
    Qwen2-7B learner via Ollama.

    Features:
    - Fast inference via Ollama
    - Reliable fallback when Pixtral unavailable
    - Text-only analysis
    - Low resource requirements
    - JSON output optimization
    """

    def __init__(
        self, model: str = "qwen2:7b", memory_manager=None, eval_agent=None, **kwargs
    ):
        """
        Initialize Qwen learner

        Args:
            model: Ollama model name (default: qwen2:7b)
            memory_manager: MemoryManager instance for storage
            eval_agent: EvalAgent for quality assessment
            **kwargs: Additional parameters (temperature, top_p, max_tokens, etc.)
        """
        self.model_name_str = model
        self.memory = memory_manager
        self.eval = eval_agent
        self.threshold = 0.75
        self.lessons: List[LearningLesson] = []

        # Accept optional parameters from kwargs
        self.temperature = kwargs.get("temperature", 0.7)
        self.top_p = kwargs.get("top_p", 0.9)
        # max_tokens removed - unlimited responses

        # Check Ollama availability
        if not OLLAMA_AVAILABLE:
            print("⚠️  Qwen initialization failed: ollama package not installed")
            print("   Install with: pip install ollama")
            self._available = False
            return

        # Test model availability
        self._check_model_availability()

    def _check_model_availability(self):
        """Check if model is available in Ollama"""
        try:
            print(f"🔍 Checking Ollama model: {self.model_name_str}")

            # Try to show model info
            ollama.show(self.model_name_str)
            print(f"✅ Qwen learner ready: {self.model_name_str}")
            self._available = True

        except Exception as e:
            print(f"⚠️  Model '{self.model_name_str}' not available in Ollama")
            print(f"   Error: {e}")
            print(f"   Available models: use 'ollama list' to check")
            print(f"   Pull model: ollama pull {self.model_name_str}")
            self._available = False

    @property
    def model_name(self) -> str:
        """Return model identifier"""
        return self.model_name_str

    def get_model_info(self) -> Dict[str, str]:
        """Return model metadata"""
        return {
            "name": "Qwen2-7B",
            "type": "text-only",
            "vision": "disabled",
            "parameters": "7B",
            "source": "ollama",
            "backend": "ollama",
            "available": str(self._available),
            "model": self.model_name_str,
        }

    def analyze_workflow(self, workflow_data: Dict) -> Dict[str, Any]:
        """
        Analyze workflow with Qwen2-7B

        Args:
            workflow_data: Workflow information dictionary

        Returns:
            Extracted lesson as dictionary
        """
        if not self._available:
            print("⚠️  Qwen not available, using fallback analysis")
            return self._fallback_analysis(workflow_data)

        try:
            # Extract workflow components
            task = workflow_data.get(
                "feature", workflow_data.get("task", "Unknown task")
            )
            pm_plan = workflow_data.get("pm_plan", "")[:200]
            architecture = workflow_data.get("architecture", "")[:200]
            implementation = workflow_data.get("implementation", "")[:200]
            score = workflow_data.get("score", 0)

            # Construct prompt
            prompt = f"""Analyze this software development workflow and return a JSON lesson.

TASK: {task}
PM PLAN: {pm_plan}
ARCHITECTURE: {architecture}
IMPLEMENTATION: {implementation}
FEEDBACK SCORE: {score:.1f}/10

Return ONLY valid JSON with this structure:
{{
    "task_description": "generalized description",
    "approach": "technical approach used",
    "success_factors": ["factor1", "factor2", "factor3"],
    "failure_factors": ["challenge1", "challenge2"],
    "semantic_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "relationships": ["concept1", "concept2", "concept3"]
}}

No markdown, no explanation, only JSON."""

            print(f"🔮 Qwen analyzing workflow...")
            print(f"   Task: {task[:60]}...")
            print(f"   Score: {score:.1f}/10")

            # Call Ollama
            response = ollama.generate(
                model=self.model_name_str,
                prompt=prompt,
                stream=False,
                options={
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "num_predict": min(self.max_tokens, 500),
                },
            )

            response_text = response.get("response", "")
            print(f"✅ Qwen response received ({len(response_text)} chars)")

            # Parse JSON
            lesson_data = self._parse_lesson_json(response_text)

            if lesson_data:
                print(f"✅ Lesson extracted successfully")
                return lesson_data
            else:
                print(f"⚠️  Failed to parse Qwen output, using fallback")
                return self._fallback_analysis(workflow_data)

        except Exception as e:
            print(f"❌ Qwen analysis error: {e}")
            import traceback

            traceback.print_exc()
            return self._fallback_analysis(workflow_data)

    def _parse_lesson_json(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from Qwen response"""
        try:
            # Try direct JSON parse
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code blocks
        json_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        matches = re.findall(json_pattern, response_text, re.DOTALL)
        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError:
                pass

        # Try to find JSON object in text
        json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
        matches = re.findall(json_pattern, response_text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        return None

    def _fallback_analysis(self, workflow_data: Dict) -> Dict[str, Any]:
        """Fallback analysis when Qwen fails"""
        task = workflow_data.get("feature", workflow_data.get("task", "Unknown"))
        return {
            "task_description": task[:200],
            "approach": "Automated workflow execution",
            "success_factors": [
                "Workflow completed successfully",
                "Positive feedback received",
                "Code generated and tested",
            ],
            "failure_factors": [
                "Automated analysis unavailable",
                "Manual review recommended",
            ],
            "semantic_tags": ["workflow", "development", "automation", "qwen-fallback"],
            "relationships": ["software-engineering", "ai-assisted-development"],
        }

    def learn_from_workflow(self, workflow_id: str) -> bool:
        """
        Main learning loop - analyze workflow and store lesson

        Args:
            workflow_id: ID of completed workflow

        Returns:
            bool: True if lesson learned successfully
        """
        if not self.memory:
            print("⚠️  No memory manager, cannot store lessons")
            return False

        try:
            # Fetch workflow data (simplified for now)
            # In real implementation, would call self.memory.get_workflow_result()
            print(f"🧠 Learning from workflow: {workflow_id}")

            # Placeholder - in production this would fetch real workflow
            workflow_data = {
                "feature": "Sample workflow task",
                "pm_plan": "Planning phase output...",
                "architecture": "Architecture design...",
                "implementation": "Implementation code...",
                "score": 8.5,
            }

            # Check threshold - normalize score to 0-1 range
            raw_score = workflow_data.get("score", 0)
            if raw_score > 1.0:
                # Score > 1.0 means it's on 0-10 scale, normalize to 0-1
                score = min(max(raw_score / 10.0, 0.0), 1.0)
                print(f"   📊 Normalized score: {raw_score} → {score:.2f}")
            else:
                score = raw_score

            if score < self.threshold:
                print(f"⚠️  Score {score:.1f} below threshold {self.threshold}")
                return False

            # Analyze with Qwen
            lesson_data = self.analyze_workflow(workflow_data)

            if not lesson_data:
                print("⚠️  No lesson data extracted")
                return False

            # Create lesson object
            lesson = LearningLesson(
                id=str(uuid.uuid4())[:8],
                workflow_id=workflow_id,
                task_description=lesson_data.get("task_description", "")[:200],
                approach=lesson_data.get("approach", "")[:300],
                success_factors=lesson_data.get("success_factors", [])[:5],
                failure_factors=lesson_data.get("failure_factors", [])[:3],
                semantic_tags=lesson_data.get("semantic_tags", [])[:10],
                relationships=lesson_data.get("relationships", [])[:10],
                score=score,
                timestamp=datetime.now(timezone.utc).isoformat(),
                model=self.model_name,
            )

            # Store via triple_write
            self.memory.triple_write(
                {
                    **lesson.to_dict(),
                    "type": "learning_lesson",
                    "source": "qwen_learner",
                    "model_info": self.get_model_info(),
                }
            )

            self.lessons.append(lesson)
            print(f"✅ Lesson learned: {lesson.id}")
            print(f"   Total lessons: {len(self.lessons)}")

            return True

        except Exception as e:
            print(f"❌ Learning error: {e}")
            import traceback

            traceback.print_exc()
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get learning statistics"""
        return {
            "total_lessons": len(self.lessons),
            "model": self.model_name,
            "model_info": self.get_model_info(),
            "threshold": self.threshold,
            "avg_score": sum(l.score for l in self.lessons) / len(self.lessons)
            if self.lessons
            else 0.0,
            "recent_lessons": [
                {
                    "id": l.id,
                    "task": l.task_description[:50],
                    "score": l.score,
                    "timestamp": l.timestamp,
                }
                for l in self.lessons[-5:]
            ],
        }

    def generate(self, prompt: str, max_tokens: Optional[int] = None, **kwargs) -> str:
        """
        Generate text via Ollama - required interface for ARCSolverAgent

        Args:
            prompt: Input prompt for generation
            max_tokens: Maximum tokens to generate (default: self.max_tokens)
            **kwargs: Additional generation parameters

        Returns:
            Generated text response
        """
        if not self._available:
            print("⚠️  Qwen not available for generation")
            return ""

        try:
            tokens = max_tokens or self.max_tokens

            response = ollama.generate(
                model=self.model_name_str,
                prompt=prompt,
                stream=False,
                options={
                    "temperature": kwargs.get("temperature", self.temperature),
                    "top_p": kwargs.get("top_p", self.top_p),
                    "num_predict": tokens,
                },
            )

            return response.get("response", "")

        except Exception as e:
            print(f"❌ Qwen generation error: {e}")
            return ""

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Chat interface via Ollama - alternative interface for ARCSolverAgent

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional chat parameters

        Returns:
            Response dict with 'message' containing 'content'
        """
        if not self._available:
            print("⚠️  Qwen not available for chat")
            return {"message": {"content": ""}}

        try:
            response = ollama.chat(
                model=self.model_name_str,
                messages=messages,
                stream=False,
                options={
                    "temperature": kwargs.get("temperature", self.temperature),
                    "top_p": kwargs.get("top_p", self.top_p),
                    "num_predict": kwargs.get("max_tokens", self.max_tokens),
                },
            )

            return response

        except Exception as e:
            print(f"❌ Qwen chat error: {e}")
            return {"message": {"content": ""}}
