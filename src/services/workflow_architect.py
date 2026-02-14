"""
MARKER_144.7: Workflow Architect — AI-powered workflow generation.

Takes a natural language description → calls Architect LLM →
returns a complete workflow (nodes + edges) ready for the DAG editor.

Uses call_model_v2 from provider_registry for direct LLM calls.
Reads preset config to determine which model to use as architect.

@phase 144
@status active
"""

import json
import uuid
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Preset → Architect Model Map ──
# Read from model_presets.json at runtime, with fallback hardcoded map
_FALLBACK_ARCHITECT_MODELS = {
    "dragon_bronze": "qwen/qwen3-30b-a3b",
    "dragon_silver": "moonshotai/kimi-k2.5",
    "dragon_gold": "moonshotai/kimi-k2.5",
    "dragon_gold_gpt": "openai/gpt-5.2",
    "titan_lite": "qwen/qwen3-30b-a3b",
    "titan_core": "google/gemini-3-pro-preview",
    "titan_prime": "anthropic/claude-opus-4.6",
    "quality": "anthropic/claude-opus-4.6",
    "polza_research": "anthropic/claude-sonnet-4",
    "polza_mixed": "anthropic/claude-sonnet-4",
}


def _load_preset_architect_model(preset: str) -> str:
    """Load architect model name from model_presets.json for the given preset."""
    try:
        presets_path = Path(__file__).parent.parent.parent / "data" / "templates" / "model_presets.json"
        if presets_path.exists():
            data = json.loads(presets_path.read_text(encoding="utf-8"))
            presets = data.get("presets", {})
            if preset in presets:
                return presets[preset]["roles"].get("architect", "moonshotai/kimi-k2.5")
    except Exception as e:
        logger.warning(f"[WorkflowArchitect] Failed to load preset config: {e}")
    return _FALLBACK_ARCHITECT_MODELS.get(preset, "moonshotai/kimi-k2.5")


def _load_preset_provider(preset: str) -> str:
    """Load provider from model_presets.json for the given preset."""
    try:
        presets_path = Path(__file__).parent.parent.parent / "data" / "templates" / "model_presets.json"
        if presets_path.exists():
            data = json.loads(presets_path.read_text(encoding="utf-8"))
            presets = data.get("presets", {})
            if preset in presets:
                return presets[preset].get("provider", "polza")
    except Exception:
        pass
    return "polza"


# ── System Prompt for Workflow Generation ──

WORKFLOW_GENERATE_SYSTEM = """You are a Workflow Architect for the VETKA AI system.
Your job: convert a natural language task description into a structured DAG workflow.

Output ONLY valid JSON with this exact format:
{
  "name": "Workflow Name",
  "description": "Brief workflow description",
  "nodes": [
    {
      "id": "n1",
      "type": "task",
      "label": "Short node label",
      "data": {
        "description": "What this node does",
        "priority": 1,
        "complexity": 1
      }
    }
  ],
  "edges": [
    {
      "id": "e1",
      "source": "n1",
      "target": "n2",
      "type": "structural"
    }
  ]
}

## Node Types (choose the most appropriate):
- "task" — a concrete implementation step (most common)
- "agent" — an AI agent role (researcher, coder, verifier). Use data.role field.
- "subtask" — a smaller step within a larger task
- "condition" — if/else branching point. Use data.expression field.
- "parallel" — fork point for concurrent execution
- "loop" — repeat with exit condition. Use data.max_iterations and data.exit_condition.
- "transform" — data transformation between steps
- "proposal" — a step that produces a plan/proposal for review

## Edge Types:
- "structural" — default sequential dependency (A must finish before B starts)
- "temporal" — time-ordered but not strictly dependent
- "conditional" — branch from a condition node. Use label: "true"/"false"
- "parallel_fork" — from a parallel node to concurrent branches
- "parallel_join" — from concurrent branches back to a join point
- "dataflow" — data passes from A to B
- "feedback" — loop-back edge (from later node back to earlier node)

## Rules:
- Generate 2-8 nodes (not too many, not too few)
- Every node needs a unique id (n1, n2, n3...)
- Every edge needs a unique id (e1, e2, e3...)
- Use "task" type for most nodes unless another type is clearly more appropriate
- For agent-style workflows, use "agent" type with data.role = "researcher" | "coder" | "verifier" | "architect"
- Node IDs in edges must reference valid node IDs
- The DAG must be acyclic (except feedback edges for loops)
- Root nodes (no incoming edges) execute first
- Assign priority: 1 (highest) for root/critical nodes, 2 for mid-level, 3 for leaf nodes
- data.complexity: 1 (simple), 2 (medium), 3 (complex)

## Position Layout:
- Assign approximate positions for visual layout
- Root nodes: position.x=200, position.y=0
- Each subsequent layer: position.y += 120
- Parallel branches: spread position.x by 200

Output ONLY the JSON object. No markdown, no comments, no explanation."""


async def generate_workflow(
    description: str,
    preset: str = "dragon_silver",
    complexity_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    MARKER_144.7: Generate a complete workflow from a natural language description.

    Uses the Architect model from the selected preset to generate a DAG workflow.

    Args:
        description: Natural language task description.
        preset: Team preset (determines which model to use).
        complexity_hint: Optional hint ("low", "medium", "high").

    Returns:
        Dict with workflow data (nodes, edges, name, description) or error.
    """
    model = _load_preset_architect_model(preset)
    provider = _load_preset_provider(preset)

    logger.info(f"[WorkflowArchitect] Generating workflow with model={model}, provider={provider}")

    # Build user prompt
    user_parts = [f"Generate a workflow for this task:\n\n{description}"]
    if complexity_hint:
        user_parts.append(f"\nComplexity hint: {complexity_hint}")
    user_content = "\n".join(user_parts)

    messages = [
        {"role": "system", "content": WORKFLOW_GENERATE_SYSTEM},
        {"role": "user", "content": user_content},
    ]

    try:
        from src.elisya.provider_registry import call_model_v2

        result = await call_model_v2(
            messages=messages,
            model=model,
            source=provider,
            temperature=0.2,  # Low temp for structured output
            max_tokens=3000,
        )

        # Extract content from response
        content = ""
        if isinstance(result, dict):
            msg = result.get("message", {})
            if isinstance(msg, dict):
                content = msg.get("content", "")
            elif isinstance(msg, str):
                content = msg
        elif isinstance(result, str):
            content = result

        if not content:
            logger.warning("[WorkflowArchitect] Empty LLM response, using fallback")
            return _generate_fallback_workflow(description, complexity_hint)

        # Parse JSON from response
        workflow = _parse_workflow_json(content)
        if workflow is None:
            logger.warning("[WorkflowArchitect] Failed to parse LLM JSON, using fallback")
            return _generate_fallback_workflow(description, complexity_hint)

        # Post-process: assign IDs, validate structure
        workflow = _post_process_workflow(workflow, description)

        # Validate
        validation = _quick_validate(workflow)
        if validation["errors"]:
            logger.warning(f"[WorkflowArchitect] Generated workflow invalid: {validation['errors']}, using fallback")
            return _generate_fallback_workflow(description, complexity_hint)

        return {
            "success": True,
            "workflow": workflow,
            "model_used": model,
            "validation": validation,
        }

    except ImportError as e:
        logger.error(f"[WorkflowArchitect] Provider registry not available: {e}")
        # Fallback: generate a simple template workflow
        return _generate_fallback_workflow(description, complexity_hint)
    except Exception as e:
        logger.error(f"[WorkflowArchitect] Generation failed: {e}")
        # Fallback to template when LLM fails (API key missing, network error, etc.)
        logger.info("[WorkflowArchitect] Using fallback template generation")
        return _generate_fallback_workflow(description, complexity_hint)


def _parse_workflow_json(content: str) -> Optional[Dict[str, Any]]:
    """Parse workflow JSON from LLM response, handling markdown code blocks."""
    # Try direct parse
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    import re
    patterns = [
        r"```json\s*\n(.*?)```",
        r"```\s*\n(.*?)```",
        r"\{.*\}",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            try:
                candidate = match.group(1) if match.lastindex else match.group(0)
                return json.loads(candidate.strip())
            except (json.JSONDecodeError, IndexError):
                continue

    return None


def _post_process_workflow(workflow: Dict[str, Any], description: str) -> Dict[str, Any]:
    """Post-process generated workflow: ensure IDs, positions, defaults."""
    # Ensure workflow ID
    if "id" not in workflow or not workflow["id"]:
        workflow["id"] = f"wf_{uuid.uuid4().hex[:8]}"

    # Ensure name
    if not workflow.get("name"):
        workflow["name"] = description[:50].strip()

    # Ensure description
    if not workflow.get("description"):
        workflow["description"] = description

    # Process nodes
    node_ids = set()
    nodes = workflow.get("nodes", [])
    for i, node in enumerate(nodes):
        # Ensure ID
        if not node.get("id"):
            node["id"] = f"n{i + 1}"
        node_ids.add(node["id"])

        # Ensure type
        if not node.get("type") or node["type"] not in {
            "task", "agent", "subtask", "proposal",
            "condition", "parallel", "loop", "transform", "group",
        }:
            node["type"] = "task"

        # Ensure label
        if not node.get("label"):
            node["label"] = f"Step {i + 1}"

        # Ensure position
        if "position" not in node:
            node["position"] = {"x": 200, "y": i * 120}
        elif isinstance(node["position"], dict):
            node["position"].setdefault("x", 200)
            node["position"].setdefault("y", i * 120)

        # Ensure data
        if "data" not in node:
            node["data"] = {}

    # Process edges
    edges = workflow.get("edges", [])
    valid_edges = []
    for i, edge in enumerate(edges):
        # Ensure ID
        if not edge.get("id"):
            edge["id"] = f"e{i + 1}"

        # Validate source/target
        source = edge.get("source", "")
        target = edge.get("target", "")
        if source in node_ids and target in node_ids:
            # Ensure type
            if not edge.get("type"):
                edge["type"] = "structural"
            valid_edges.append(edge)
        else:
            logger.warning(
                f"[WorkflowArchitect] Dropping edge {edge.get('id')}: "
                f"invalid source={source} or target={target}"
            )

    workflow["edges"] = valid_edges

    # Ensure metadata
    if "metadata" not in workflow:
        workflow["metadata"] = {}
    workflow["metadata"]["generated"] = True
    workflow["metadata"]["generator"] = "workflow_architect_v1"

    return workflow


def _quick_validate(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """Quick structural validation (lighter than full WorkflowStore.validate)."""
    errors = []
    warnings = []

    nodes = workflow.get("nodes", [])
    edges = workflow.get("edges", [])

    if not nodes:
        errors.append("No nodes in workflow")
        return {"valid": False, "errors": errors, "warnings": warnings}

    node_ids = {n["id"] for n in nodes}

    # Check for duplicate IDs
    if len(node_ids) != len(nodes):
        errors.append("Duplicate node IDs detected")

    # Check edges reference valid nodes
    for edge in edges:
        if edge.get("source") not in node_ids:
            errors.append(f"Edge {edge.get('id')}: invalid source {edge.get('source')}")
        if edge.get("target") not in node_ids:
            errors.append(f"Edge {edge.get('id')}: invalid target {edge.get('target')}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }


def _generate_fallback_workflow(
    description: str,
    complexity_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a simple template workflow when the LLM is not available.
    Creates a basic sequential pipeline: Research → Plan → Implement → Verify.
    """
    complexity = complexity_hint or "medium"

    if complexity == "low":
        nodes = [
            {"id": "n1", "type": "task", "label": "Implement", "position": {"x": 200, "y": 0},
             "data": {"description": description, "priority": 1, "complexity": 1}},
            {"id": "n2", "type": "agent", "label": "Verify", "position": {"x": 200, "y": 120},
             "data": {"description": "Verify the implementation", "role": "verifier", "priority": 2, "complexity": 1}},
        ]
        edges = [
            {"id": "e1", "source": "n1", "target": "n2", "type": "structural"},
        ]
    elif complexity == "high":
        nodes = [
            {"id": "n1", "type": "agent", "label": "Research", "position": {"x": 200, "y": 0},
             "data": {"description": f"Research: {description}", "role": "researcher", "priority": 1, "complexity": 2}},
            {"id": "n2", "type": "agent", "label": "Plan", "position": {"x": 200, "y": 120},
             "data": {"description": "Plan the implementation", "role": "architect", "priority": 1, "complexity": 2}},
            {"id": "n3", "type": "task", "label": "Implement Core", "position": {"x": 100, "y": 240},
             "data": {"description": "Implement core functionality", "priority": 2, "complexity": 3}},
            {"id": "n4", "type": "task", "label": "Implement UI", "position": {"x": 300, "y": 240},
             "data": {"description": "Implement UI/frontend", "priority": 2, "complexity": 2}},
            {"id": "n5", "type": "task", "label": "Integration", "position": {"x": 200, "y": 360},
             "data": {"description": "Integrate components", "priority": 3, "complexity": 2}},
            {"id": "n6", "type": "agent", "label": "Verify", "position": {"x": 200, "y": 480},
             "data": {"description": "Verify the complete implementation", "role": "verifier", "priority": 3, "complexity": 1}},
        ]
        edges = [
            {"id": "e1", "source": "n1", "target": "n2", "type": "structural"},
            {"id": "e2", "source": "n2", "target": "n3", "type": "structural"},
            {"id": "e3", "source": "n2", "target": "n4", "type": "structural"},
            {"id": "e4", "source": "n3", "target": "n5", "type": "structural"},
            {"id": "e5", "source": "n4", "target": "n5", "type": "structural"},
            {"id": "e6", "source": "n5", "target": "n6", "type": "structural"},
        ]
    else:
        # Medium complexity (default)
        nodes = [
            {"id": "n1", "type": "agent", "label": "Research", "position": {"x": 200, "y": 0},
             "data": {"description": f"Research: {description}", "role": "researcher", "priority": 1, "complexity": 1}},
            {"id": "n2", "type": "task", "label": "Implement", "position": {"x": 200, "y": 120},
             "data": {"description": description, "priority": 2, "complexity": 2}},
            {"id": "n3", "type": "agent", "label": "Verify", "position": {"x": 200, "y": 240},
             "data": {"description": "Verify the implementation", "role": "verifier", "priority": 3, "complexity": 1}},
        ]
        edges = [
            {"id": "e1", "source": "n1", "target": "n2", "type": "structural"},
            {"id": "e2", "source": "n2", "target": "n3", "type": "structural"},
        ]

    workflow = {
        "id": f"wf_{uuid.uuid4().hex[:8]}",
        "name": description[:50].strip(),
        "description": description,
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "generated": True,
            "generator": "workflow_architect_fallback",
            "complexity_hint": complexity,
        },
    }

    return {
        "success": True,
        "workflow": workflow,
        "model_used": "fallback_template",
        "validation": _quick_validate(workflow),
    }
