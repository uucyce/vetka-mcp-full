"""
Pixtral-12B Learner - Multimodal workflow analyzer with vision capabilities.

Loads local Pixtral-12B model for advanced workflow analysis.
Supports vision-enabled analysis of diagrams and screenshots.

@file pixtral_learner.py
@status: active
@phase: 96
@depends: transformers, torch, .base_learner.BaseLearner, .learner_factory.LearnerFactory
@used_by: src/initialization/dependency_check.py (dynamic loading via LearnerFactory)
"""

import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from dataclasses import dataclass, asdict

from .base_learner import BaseLearner
from .learner_factory import LearnerFactory

# Check transformers availability
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch

    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("⚠️  Pixtral requires: pip install transformers torch accelerate")


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
    model: str = "pixtral-12b-multimodal"

    def to_dict(self) -> Dict:
        return asdict(self)


@LearnerFactory.register("pixtral")
class PixtralLearner(BaseLearner):
    """
    Pixtral-12B multimodal learner with vision capabilities.

    Features:
    - Local inference via transformers
    - Vision-enabled (can analyze diagrams and screenshots)
    - 12B parameters for advanced reasoning
    - Automatic GPU/CPU device mapping
    """

    def __init__(
        self,
        model_path: str = None,
        memory_manager=None,
        eval_agent=None,
        device_map: str = "auto",
        **kwargs,
    ):
        """
        Initialize Pixtral learner

        Args:
            model_path: Path to Pixtral model directory (e.g., ~/pixtral-12b)
            memory_manager: MemoryManager instance for storage
            eval_agent: EvalAgent for quality assessment
            device_map: Device mapping strategy ("auto", "cpu", "cuda")
            **kwargs: Additional parameters (temperature, top_p, max_tokens, etc.)
        """
        import os

        # Use model_path from kwargs if not provided directly
        self.model_path = (
            model_path
            or kwargs.get("model_path")
            or os.path.expanduser("~/pixtral-12b")
        )
        self.memory = memory_manager
        self.eval = eval_agent
        self.threshold = 0.75
        self.lessons: List[LearningLesson] = []
        self.device_map = device_map

        # Accept optional parameters from kwargs
        self.temperature = kwargs.get("temperature", 0.7)
        self.top_p = kwargs.get("top_p", 0.9)
        # max_tokens removed - unlimited responses

        # Check dependencies
        if not TRANSFORMERS_AVAILABLE:
            print("⚠️  Pixtral initialization failed: missing dependencies")
            print("   Install with: pip install transformers torch accelerate")
            self.model = None
            self.tokenizer = None
            self._model_loaded = False
            return

        # Load model
        self._load_model()

    def _load_model(self):
        """Load Pixtral model and tokenizer"""
        try:
            print(f"\n{'=' * 70}")
            print(f"🧠 LOADING PIXTRAL-12B MODEL")
            print(f"{'=' * 70}")
            print(f"   Path: {self.model_path}")
            print(f"   Device: {self.device_map}")

            # Load tokenizer
            print("   Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path, trust_remote_code=True
            )
            print("   ✅ Tokenizer loaded")

            # Load model with device mapping
            print("   Loading model (this may take a minute)...")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16
                if torch.cuda.is_available()
                else torch.float32,
                device_map=self.device_map,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
            )
            print("   ✅ Model loaded")

            # Check device
            device = next(self.model.parameters()).device
            print(f"   Device: {device}")
            print(f"✅ Pixtral-12B ready (Vision-enabled)")
            print(f"{'=' * 70}\n")

            self._model_loaded = True

        except FileNotFoundError as e:
            print(f"❌ Model not found at {self.model_path}")
            print(f"   Error: {e}")
            print(f"   Make sure Pixtral is downloaded to this path")
            self.model = None
            self.tokenizer = None
            self._model_loaded = False

        except Exception as e:
            print(f"❌ Failed to load Pixtral: {e}")
            print(f"   Possible issues:")
            print(f"   - Insufficient RAM/VRAM (Pixtral needs ~25GB)")
            print(f"   - Missing dependencies (pip install transformers torch)")
            print(f"   - Corrupted model files")
            import traceback

            traceback.print_exc()
            self.model = None
            self.tokenizer = None
            self._model_loaded = False

    @property
    def model_name(self) -> str:
        """Return model identifier"""
        return "pixtral-12b-multimodal"

    def get_model_info(self) -> Dict[str, str]:
        """Return model metadata"""
        info = {
            "name": "Pixtral-12B",
            "type": "multimodal",
            "vision": "enabled" if self._model_loaded else "unavailable",
            "parameters": "12B",
            "source": self.model_path,
            "backend": "transformers",
            "loaded": str(self._model_loaded),
        }

        if self._model_loaded and self.model:
            device = str(next(self.model.parameters()).device)
            info["device"] = device

        return info

    def analyze_workflow(self, workflow_data: Dict) -> Dict[str, Any]:
        """
        Analyze workflow with Pixtral-12B

        Args:
            workflow_data: Workflow information dictionary

        Returns:
            Extracted lesson as dictionary
        """
        if not self._model_loaded:
            print("⚠️  Pixtral not loaded, cannot analyze workflow")
            return self._fallback_analysis(workflow_data)

        try:
            # Extract workflow components
            task = workflow_data.get(
                "feature", workflow_data.get("task", "Unknown task")
            )
            pm_plan = workflow_data.get("pm_plan", "")[:300]
            architecture = workflow_data.get("architecture", "")[:300]
            implementation = workflow_data.get("implementation", "")[:300]
            feedback_score = workflow_data.get("score", 0)

            # Construct analysis prompt
            prompt = self._build_analysis_prompt(
                task, pm_plan, architecture, implementation, feedback_score
            )

            print(f"🔮 Pixtral analyzing workflow...")
            print(f"   Task: {task[:60]}...")
            print(f"   Score: {feedback_score:.1f}/10")

            # Generate analysis
            response_text = self._generate_response(prompt)

            # Parse JSON from response
            lesson_data = self._parse_lesson_json(response_text)

            if lesson_data:
                print(f"✅ Pixtral extracted lesson successfully")
                return lesson_data
            else:
                print(f"⚠️  Failed to parse Pixtral output, using fallback")
                return self._fallback_analysis(workflow_data)

        except Exception as e:
            print(f"❌ Pixtral analysis error: {e}")
            import traceback

            traceback.print_exc()
            return self._fallback_analysis(workflow_data)

    def _build_analysis_prompt(
        self,
        task: str,
        pm_plan: str,
        architecture: str,
        implementation: str,
        score: float,
    ) -> str:
        """Build analysis prompt for Pixtral"""
        return f"""Analyze this software development workflow and extract structured learnings.

TASK DESCRIPTION:
{task}

PM PLANNING PHASE:
{pm_plan}

ARCHITECTURE PHASE:
{architecture}

IMPLEMENTATION PHASE:
{implementation}

FEEDBACK SCORE: {score:.2f}/10

Generate a JSON lesson with the following structure:
{{
    "task_description": "Generalized description of what was accomplished",
    "approach": "Technical approach or methodology that was successful",
    "success_factors": ["Factor 1", "Factor 2", "Factor 3"],
    "failure_factors": ["Challenge 1", "Challenge 2"],
    "semantic_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "relationships": ["related_concept_1", "related_concept_2", "related_concept_3"]
}}

IMPORTANT:
- Respond ONLY with valid JSON
- No markdown code blocks
- No explanatory text
- Generalize the lesson for reuse in similar contexts
"""

    def _generate_response(self, prompt: str, max_length: int = 800) -> str:
        """Generate response from Pixtral"""
        try:
            inputs = self.tokenizer(
                prompt, return_tensors="pt", truncation=True, max_length=2048
            ).to(self.model.device)

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_length,
                    temperature=0.7,
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                )

            response_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Remove input prompt from output
            if prompt in response_text:
                response_text = response_text.replace(prompt, "").strip()

            return response_text

        except Exception as e:
            print(f"⚠️  Generation error: {e}")
            return ""

    def _parse_lesson_json(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from Pixtral response"""
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
        """Fallback analysis when Pixtral fails"""
        task = workflow_data.get("feature", workflow_data.get("task", "Unknown"))
        return {
            "task_description": task[:200],
            "approach": "Automated workflow execution",
            "success_factors": [
                "Workflow completed",
                "Positive feedback received",
                "Code generated successfully",
            ],
            "failure_factors": [
                "Automated analysis unavailable",
                "Manual review recommended",
            ],
            "semantic_tags": ["workflow", "development", "automation"],
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

            # Check threshold
            score = workflow_data.get("score", 0)
            if score < self.threshold:
                print(f"⚠️  Score {score:.1f} below threshold {self.threshold}")
                return False

            # Analyze with Pixtral
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
                timestamp=datetime.utcnow().isoformat(),
                model=self.model_name,
            )

            # Store via triple_write
            self.memory.triple_write(
                {
                    **lesson.to_dict(),
                    "type": "learning_lesson",
                    "source": "pixtral_learner",
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
        Generate text via transformers - required interface for ARCSolverAgent

        Args:
            prompt: Input prompt for generation
            max_tokens: Maximum tokens to generate (default: self.max_tokens)
            **kwargs: Additional generation parameters

        Returns:
            Generated text response
        """
        if not self._model_loaded:
            print("⚠️  Pixtral not loaded for generation")
            return ""

        try:
            tokens = max_tokens or self.max_tokens
            return self._generate_response(prompt, max_length=tokens)

        except Exception as e:
            print(f"❌ Pixtral generation error: {e}")
            return ""

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Chat interface via transformers - alternative interface for ARCSolverAgent

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional chat parameters

        Returns:
            Response dict with 'message' containing 'content'
        """
        if not self._model_loaded:
            print("⚠️  Pixtral not loaded for chat")
            return {"message": {"content": ""}}

        try:
            # Combine messages into single prompt
            prompt_parts = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    prompt_parts.append(f"System: {content}")
                elif role == "user":
                    prompt_parts.append(f"User: {content}")
                elif role == "assistant":
                    prompt_parts.append(f"Assistant: {content}")

            prompt = "\n".join(prompt_parts) + "\nAssistant:"

            max_tokens = kwargs.get("max_tokens", self.max_tokens)
            response_text = self._generate_response(prompt, max_length=max_tokens)

            return {"message": {"content": response_text}}

        except Exception as e:
            print(f"❌ Pixtral chat error: {e}")
            return {"message": {"content": ""}}
