"""
MARKER_144.9: ComfyUI ↔ VETKA Workflow Converter.

Bidirectional conversion between ComfyUI workflow JSON and VETKA format.
Lossy in both directions — documented below.

ComfyUI API format:
  - Prompt dict: {node_id_str: {class_type, inputs{param: value_or_link}}}
  - Links are embedded in inputs: [from_node_id, output_slot_index]
  - No explicit edges array — connections inferred from input values

ComfyUI Graph format (exported from UI):
  - nodes[]: {id(int), type, pos[x,y], size{}, widgets_values[], inputs[], outputs[]}
  - links[]: [link_id, from_id, from_slot, to_id, to_slot, link_type]

This converter handles BOTH formats with auto-detection.

@phase 144
@status active
"""

import uuid
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── Node Type Mapping ──

# VETKA → ComfyUI
VETKA_TO_COMFYUI_TYPE = {
    "task": "VETKATask",
    "agent": "VETKAAgent",
    "subtask": "VETKATask",
    "proposal": "PreviewText",
    "condition": "VETKACondition",
    "parallel": "VETKAParallel",
    "loop": "VETKALoop",
    "transform": "VETKATransform",
    "group": "Reroute",
}

# ComfyUI → VETKA (common ComfyUI node types)
COMFYUI_TO_VETKA_TYPE = {
    # Model loading
    "CheckpointLoaderSimple": "agent",
    "CheckpointLoader": "agent",
    "LoraLoader": "agent",
    "LoraLoaderModelOnly": "agent",
    "CLIPLoader": "agent",
    "VAELoader": "agent",
    "ControlNetLoader": "agent",
    "UNETLoader": "agent",
    # Sampling
    "KSampler": "task",
    "KSamplerAdvanced": "task",
    "SamplerCustom": "task",
    # Conditioning / prompt
    "CLIPTextEncode": "transform",
    "ConditioningCombine": "transform",
    "ConditioningSetArea": "transform",
    # VAE / image ops
    "VAEDecode": "transform",
    "VAEEncode": "transform",
    "ImageScale": "transform",
    "ImageUpscaleWithModel": "transform",
    # Preview / output
    "PreviewImage": "proposal",
    "SaveImage": "proposal",
    "PreviewText": "proposal",
    # Utility
    "Reroute": "group",
    "Note": "proposal",
    "PrimitiveNode": "transform",
    # VETKA roundtrip types
    "VETKATask": "task",
    "VETKAAgent": "agent",
    "VETKACondition": "condition",
    "VETKAParallel": "parallel",
    "VETKALoop": "loop",
    "VETKATransform": "transform",
}


def detect_comfyui_format(data: Dict[str, Any]) -> str:
    """
    Detect ComfyUI format type.
    Returns: 'graph' (UI export), 'api' (API prompt), or 'none'.
    """
    if not isinstance(data, dict):
        return "none"

    # Graph format: has "nodes" array and "links" array
    if isinstance(data.get("nodes"), list) and isinstance(data.get("links"), list):
        nodes = data["nodes"]
        if nodes and isinstance(nodes[0], dict) and "type" in nodes[0]:
            return "graph"

    # API format: dict of dicts with "class_type" keys
    if all(
        isinstance(v, dict) and "class_type" in v
        for v in data.values()
        if isinstance(v, dict)
    ) and len(data) > 0:
        # Check at least one value has class_type
        has_class = any(
            isinstance(v, dict) and "class_type" in v
            for v in data.values()
        )
        if has_class:
            return "api"

    return "none"


def comfyui_to_vetka(comfyui_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert ComfyUI workflow → VETKA workflow format.
    Auto-detects graph vs API format.
    """
    fmt = detect_comfyui_format(comfyui_data)
    if fmt == "graph":
        return _comfyui_graph_to_vetka(comfyui_data)
    elif fmt == "api":
        return _comfyui_api_to_vetka(comfyui_data)
    else:
        raise ValueError("Unknown ComfyUI format — expected graph or API prompt format")


def _comfyui_graph_to_vetka(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert ComfyUI graph (UI export) format → VETKA."""
    comfy_nodes = data.get("nodes", [])
    comfy_links = data.get("links", [])

    # Build node map: comfy node id → VETKA node
    vetka_nodes: List[Dict[str, Any]] = []
    comfy_id_to_vetka_id: Dict[int, str] = {}

    for i, cnode in enumerate(comfy_nodes):
        comfy_id = cnode.get("id", i)
        vetka_id = f"n{i + 1}"
        comfy_id_to_vetka_id[comfy_id] = vetka_id

        class_type = cnode.get("type", "Unknown")
        vetka_type = COMFYUI_TO_VETKA_TYPE.get(class_type, "transform")

        # Position: ComfyUI uses [x, y] array
        pos = cnode.get("pos", [0, 0])
        if isinstance(pos, list) and len(pos) >= 2:
            position = {"x": pos[0], "y": pos[1]}
        elif isinstance(pos, dict):
            position = {"x": pos.get("0", pos.get("x", 0)), "y": pos.get("1", pos.get("y", 0))}
        else:
            position = {"x": i * 200, "y": 0}

        # Build data with ComfyUI metadata
        node_data: Dict[str, Any] = {
            "description": f"ComfyUI: {class_type}",
            "comfyui_class_type": class_type,
        }

        # Preserve widget values
        widgets = cnode.get("widgets_values", [])
        if widgets:
            node_data["comfyui_widgets"] = widgets

        # Preserve properties
        props = cnode.get("properties", {})
        if props:
            node_data["comfyui_properties"] = props

        label = cnode.get("title", "") or class_type

        vetka_nodes.append({
            "id": vetka_id,
            "type": vetka_type,
            "label": label,
            "position": position,
            "data": node_data,
        })

    # Parse links → edges
    # ComfyUI link format: [link_id, from_node_id, from_slot, to_node_id, to_slot, type_str]
    vetka_edges: List[Dict[str, Any]] = []
    for link in comfy_links:
        if not isinstance(link, list) or len(link) < 5:
            continue

        link_id = link[0]
        from_id = link[1]
        from_slot = link[2]
        to_id = link[3]
        to_slot = link[4]

        source = comfy_id_to_vetka_id.get(from_id)
        target = comfy_id_to_vetka_id.get(to_id)
        if not source or not target:
            continue

        # Determine edge type based on slot names/types
        edge_type = "dataflow"  # ComfyUI connections are primarily data flow

        vetka_edges.append({
            "id": f"e{link_id}",
            "source": source,
            "target": target,
            "type": edge_type,
            "data": {
                "from_slot": from_slot,
                "to_slot": to_slot,
                "comfyui_link_type": link[5] if len(link) > 5 else None,
            },
        })

    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": f"wf_{uuid.uuid4().hex[:8]}",
        "name": data.get("extra", {}).get("title", "Imported ComfyUI Workflow"),
        "description": f"Imported from ComfyUI graph ({len(vetka_nodes)} nodes)",
        "nodes": vetka_nodes,
        "edges": vetka_edges,
        "metadata": {
            "created_at": now,
            "updated_at": now,
            "version": 1,
            "imported_from": "comfyui_graph",
        },
    }


def _comfyui_api_to_vetka(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert ComfyUI API prompt format → VETKA."""
    vetka_nodes: List[Dict[str, Any]] = []
    vetka_edges: List[Dict[str, Any]] = []
    edge_counter = 0

    # API format: {str_id: {class_type, inputs{...}}}
    node_ids = sorted(data.keys(), key=lambda x: int(x) if x.isdigit() else 0)
    comfy_id_to_vetka_id: Dict[str, str] = {}

    for i, comfy_id in enumerate(node_ids):
        node_def = data[comfy_id]
        if not isinstance(node_def, dict) or "class_type" not in node_def:
            continue

        vetka_id = f"n{i + 1}"
        comfy_id_to_vetka_id[comfy_id] = vetka_id

        class_type = node_def["class_type"]
        vetka_type = COMFYUI_TO_VETKA_TYPE.get(class_type, "transform")

        # No position in API format — generate grid layout
        row = i // 4
        col = i % 4
        position = {"x": col * 250, "y": row * 150}

        node_data: Dict[str, Any] = {
            "description": f"ComfyUI: {class_type}",
            "comfyui_class_type": class_type,
        }

        # Separate link-type inputs from value inputs
        inputs = node_def.get("inputs", {})
        value_inputs = {}
        for key, val in inputs.items():
            if isinstance(val, list) and len(val) == 2 and isinstance(val[0], (str, int)):
                # This is a link: [from_node_id, output_slot]
                pass  # handled in edge creation below
            else:
                value_inputs[key] = val

        if value_inputs:
            node_data["comfyui_inputs"] = value_inputs

        vetka_nodes.append({
            "id": vetka_id,
            "type": vetka_type,
            "label": class_type,
            "position": position,
            "data": node_data,
        })

    # Extract edges from input links
    for comfy_id in node_ids:
        node_def = data.get(comfy_id, {})
        if not isinstance(node_def, dict):
            continue
        inputs = node_def.get("inputs", {})
        target_id = comfy_id_to_vetka_id.get(comfy_id)
        if not target_id:
            continue

        for key, val in inputs.items():
            if isinstance(val, list) and len(val) == 2:
                source_comfy_id = str(val[0])
                source_slot = val[1]
                source_id = comfy_id_to_vetka_id.get(source_comfy_id)
                if not source_id:
                    continue

                edge_counter += 1
                vetka_edges.append({
                    "id": f"e{edge_counter}",
                    "source": source_id,
                    "target": target_id,
                    "type": "dataflow",
                    "data": {
                        "input_name": key,
                        "from_slot": source_slot,
                    },
                })

    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": f"wf_{uuid.uuid4().hex[:8]}",
        "name": "Imported ComfyUI Prompt",
        "description": f"Imported from ComfyUI API ({len(vetka_nodes)} nodes)",
        "nodes": vetka_nodes,
        "edges": vetka_edges,
        "metadata": {
            "created_at": now,
            "updated_at": now,
            "version": 1,
            "imported_from": "comfyui_api",
        },
    }


def vetka_to_comfyui(workflow: Dict[str, Any], fmt: str = "graph") -> Dict[str, Any]:
    """
    Convert VETKA workflow → ComfyUI format.

    Args:
        workflow: VETKA workflow dict
        fmt: 'graph' for UI format, 'api' for API prompt format
    """
    if fmt == "api":
        return _vetka_to_comfyui_api(workflow)
    return _vetka_to_comfyui_graph(workflow)


def _vetka_to_comfyui_graph(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """Convert VETKA → ComfyUI graph (UI) format."""
    vetka_nodes = workflow.get("nodes", [])
    vetka_edges = workflow.get("edges", [])

    # Build VETKA id → numeric ComfyUI id
    vetka_to_comfy_id: Dict[str, int] = {}
    comfy_nodes: List[Dict[str, Any]] = []

    for i, vnode in enumerate(vetka_nodes):
        node_id = vnode.get("id", f"n{i}")
        comfy_id = i + 1
        vetka_to_comfy_id[node_id] = comfy_id

        vetka_type = vnode.get("type", "task")
        data = vnode.get("data", {})
        pos = vnode.get("position", {"x": 0, "y": 0})

        # Use original class_type if available (round-trip), else map
        class_type = data.get("comfyui_class_type") or VETKA_TO_COMFYUI_TYPE.get(vetka_type, "VETKATask")

        comfy_node: Dict[str, Any] = {
            "id": comfy_id,
            "type": class_type,
            "pos": [pos.get("x", 0), pos.get("y", 0)],
            "size": {"0": 210, "1": 120},
            "mode": 0,
            "title": vnode.get("label", class_type),
            "properties": data.get("comfyui_properties", {}),
            "widgets_values": data.get("comfyui_widgets", []),
            "inputs": [],
            "outputs": [{"name": "output", "type": "*", "links": []}],
        }

        comfy_nodes.append(comfy_node)

    # Build links from edges
    # ComfyUI link: [link_id, from_id, from_slot, to_id, to_slot, type_str]
    comfy_links: List[List] = []
    link_counter = 0

    for edge in vetka_edges:
        source_id = vetka_to_comfy_id.get(edge.get("source", ""))
        target_id = vetka_to_comfy_id.get(edge.get("target", ""))
        if not source_id or not target_id:
            continue

        link_counter += 1
        from_slot = edge.get("data", {}).get("from_slot", 0)
        to_slot = edge.get("data", {}).get("to_slot", 0)
        link_type = edge.get("data", {}).get("comfyui_link_type", "*")

        comfy_links.append([
            link_counter,
            source_id,
            from_slot,
            target_id,
            to_slot,
            link_type,
        ])

        # Update node inputs/outputs for link tracking
        for cn in comfy_nodes:
            if cn["id"] == target_id:
                cn["inputs"].append({
                    "name": f"input_{to_slot}",
                    "type": link_type,
                    "link": link_counter,
                })
            if cn["id"] == source_id:
                if cn["outputs"] and "links" in cn["outputs"][0]:
                    cn["outputs"][0]["links"].append(link_counter)

    return {
        "last_node_id": len(comfy_nodes),
        "last_link_id": link_counter,
        "nodes": comfy_nodes,
        "links": comfy_links,
        "groups": [],
        "config": {},
        "extra": {
            "title": workflow.get("name", "VETKA Export"),
            "exported_from": "vetka",
        },
        "version": 0.4,
    }


def _vetka_to_comfyui_api(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """Convert VETKA → ComfyUI API prompt format."""
    vetka_nodes = workflow.get("nodes", [])
    vetka_edges = workflow.get("edges", [])

    # Build node ID → numeric string map
    vetka_to_comfy_id: Dict[str, str] = {}
    prompt: Dict[str, Dict] = {}

    for i, vnode in enumerate(vetka_nodes):
        node_id = vnode.get("id", f"n{i}")
        comfy_id = str(i + 1)
        vetka_to_comfy_id[node_id] = comfy_id

        data = vnode.get("data", {})
        vetka_type = vnode.get("type", "task")

        class_type = data.get("comfyui_class_type") or VETKA_TO_COMFYUI_TYPE.get(vetka_type, "VETKATask")

        # Restore original inputs or create empty
        inputs = dict(data.get("comfyui_inputs", {}))

        prompt[comfy_id] = {
            "class_type": class_type,
            "inputs": inputs,
        }

    # Wire edges as input links
    for edge in vetka_edges:
        source_comfy = vetka_to_comfy_id.get(edge.get("source", ""))
        target_comfy = vetka_to_comfy_id.get(edge.get("target", ""))
        if not source_comfy or not target_comfy:
            continue

        from_slot = edge.get("data", {}).get("from_slot", 0)
        input_name = edge.get("data", {}).get("input_name", f"input_{from_slot}")

        if target_comfy in prompt:
            prompt[target_comfy]["inputs"][input_name] = [source_comfy, from_slot]

    return prompt
