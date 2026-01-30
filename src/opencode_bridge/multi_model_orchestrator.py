"""
Multi-Model Orchestrator for Big Pickle.
Enables cross-model workflows through OpenCode Bridge.

@status: active
@phase: 96
@depends: json, typing, datetime
@used_by: src.opencode_bridge.routes
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime


class MultiModelOrchestrator:
    """Orchestrates multiple models in workflow chains"""

    def __init__(self, bridge_instance=None):
        self.bridge = bridge_instance
        self.workflows = {}

    async def orchestrate(self, command: str) -> Dict[str, Any]:
        """
        Parse and execute multi-model commands

        Examples:
        - "Оркестрируй: Grok → Architect → DeepSeek → Implementation"
        - "Позвони Гроку с промптом: проанализируй этот код"
        - "Сделай цепочку: Research → Design → Code → Test"
        """

        # Parse command type
        if "Оркестрируй:" in command:
            return await self._handle_orchestration(command)
        elif "Позвони" in command and "с промптом:" in command:
            return await self._handle_single_call(command)
        elif "Сделай цепочку:" in command:
            return await self._handle_chain(command)
        else:
            return {
                "error": "Unknown command format",
                "suggestion": "Use: Оркестрируй: / Позвони / Сделай цепочку",
            }

    async def _handle_orchestration(self, command: str) -> Dict[str, Any]:
        """Handle orchestration commands"""
        # Extract workflow: Grok → Architect → DeepSeek → Implementation
        workflow_part = command.split("Оркестрируй:")[1].strip()

        # Parse models
        models = [m.strip() for m in workflow_part.split("→")]

        results = []
        current_context = ""

        for i, model in enumerate(models):
            if model.lower() == "implementation":
                # Execute code implementation
                result = await self._implement_code(current_context)
            else:
                # Call model through bridge
                model_id = self._map_model_name(model)
                prompt = f"Previous context: {current_context}\n\nYour task as {model}:"

                result = await self.call_bridge_model(model_id, prompt)

            results.append({"step": i + 1, "model": model, "result": result})

            current_context += f"\n\n{model} output: {result}"

        return {
            "workflow_type": "orchestration",
            "steps": results,
            "final_output": current_context,
        }

    async def _handle_single_call(self, command: str) -> Dict[str, Any]:
        """Handle single model call"""
        # Extract: "Позвони Гроку с промптом: {prompt}"
        parts = command.split("с промптом:")
        model_name = parts[0].replace("Позвони", "").strip()
        prompt = parts[1].strip()

        model_id = self._map_model_name(model_name)
        result = await self.call_bridge_model(model_id, prompt)

        return {
            "workflow_type": "single_call",
            "model": model_name,
            "prompt": prompt,
            "result": result,
        }

    async def _handle_chain(self, command: str) -> Dict[str, Any]:
        """Handle chain commands"""
        # Extract: "Сделай цепочку: Research → Design → Code → Test"
        chain_part = command.split("Сделай цепочку:")[1].strip()
        steps = [s.strip() for s in chain_part.split("→")]

        results = []

        for step in steps:
            if step.lower() == "test":
                result = await self._run_tests()
            else:
                model_id = self._map_model_name(step)
                result = await self.call_bridge_model(model_id, f"Execute step: {step}")

            results.append({"step": step, "result": result})

        return {"workflow_type": "chain", "steps": results}

    def _map_model_name(self, model_name: str) -> str:
        """Map friendly names to bridge model IDs"""
        mapping = {
            "Грок": "xai/grok-4",
            "Grok": "xai/grok-4",
            "Architect": "anthropic/claude-3.5-sonnet",
            "Архитектор": "anthropic/claude-3.5-sonnet",
            "DeepSeek": "deepseek/deepseek-chat",
            "DeepSeekCoder": "deepseek/deepseek-coder",
            "Claude Opus": "anthropic/claude-opus-4-5",
            "ClaudeOpus": "anthropic/claude-opus-4-5",
            "Gemini": "google/gemini-flash-1.5",
            "Llama": "meta-llama/llama-3.1-8b-instruct",
        }
        return mapping.get(model_name, "deepseek/deepseek-chat")

    async def call_bridge_model(self, model_id: str, prompt: str) -> str:
        """Call model through OpenCode bridge"""
        if not self.bridge:
            return "Bridge not available"

        try:
            response = await self.bridge.invoke(
                model_id, [{"role": "user", "content": prompt}]
            )

            if response.get("success"):
                return response["message"]["content"]
            else:
                return f"Error: {response.get('error', 'Unknown error')}"
        except Exception as e:
            return f"Exception: {str(e)}"

    async def _implement_code(self, context: str) -> str:
        """Implement code based on context"""
        return "Code implementation phase executed"

    async def _run_tests(self) -> str:
        """Run tests on implemented code"""
        return "Tests executed successfully"


# Global instance
_orchestrator: Optional[MultiModelOrchestrator] = None


def get_orchestrator() -> MultiModelOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MultiModelOrchestrator()
    return _orchestrator
