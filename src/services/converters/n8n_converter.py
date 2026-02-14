"""
MARKER_144.8: n8n ↔ VETKA Workflow Converter.

Bidirectional conversion between n8n workflow JSON and VETKA workflow format.
Lossy in both directions — documented in mapping tables below.

n8n format reference:
  - nodes[]: {id, name, type, typeVersion, position[x,y], parameters{}}
  - connections: {nodeFrom: {outputType: [{node, type, index}]}}

VETKA format reference:
  - nodes[]: {id, type, label, position{x,y}, data{}}
  - edges[]: {id, source, target, type, label?}

@phase 144
@status active
"""

import uuid
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── Node Type Mapping ──

# VETKA → n8n
VETKA_TO_N8N_TYPE = {
    "task": "n8n-nodes-base.code",
    "agent": "n8n-nodes-base.httpRequest",
    "subtask": "n8n-nodes-base.code",
    "proposal": "n8n-nodes-base.noOp",
    "condition": "n8n-nodes-base.if",
    "parallel": "n8n-nodes-base.splitInBatches",
    "loop": "n8n-nodes-base.splitInBatches",
    "transform": "n8n-nodes-base.set",
    "group": "n8n-nodes-base.noOp",
}

# n8n → VETKA (reverse mapping — many-to-one)
N8N_TO_VETKA_TYPE = {
    # Execution nodes
    "n8n-nodes-base.code": "task",
    "n8n-nodes-base.executeCommand": "task",
    "n8n-nodes-base.function": "task",
    "n8n-nodes-base.functionItem": "task",
    "n8n-nodes-base.executeWorkflow": "task",
    # HTTP/API nodes
    "n8n-nodes-base.httpRequest": "agent",
    "n8n-nodes-base.webhook": "agent",
    "@n8n/n8n-nodes-langchain.agent": "agent",
    "@n8n/n8n-nodes-langchain.chainLlm": "agent",
    # Control flow
    "n8n-nodes-base.if": "condition",
    "n8n-nodes-base.switch": "condition",
    "n8n-nodes-base.filter": "condition",
    # Parallel / batch
    "n8n-nodes-base.splitInBatches": "parallel",
    "n8n-nodes-base.merge": "parallel",
    # Loop
    "n8n-nodes-base.loop": "loop",
    # Data transform
    "n8n-nodes-base.set": "transform",
    "n8n-nodes-base.itemLists": "transform",
    "n8n-nodes-base.spreadsheetFile": "transform",
    "n8n-nodes-base.convertToFile": "transform",
    # NoOp / markers
    "n8n-nodes-base.noOp": "proposal",
    "n8n-nodes-base.start": "task",
    "n8n-nodes-base.manualTrigger": "task",
    "n8n-nodes-base.scheduleTrigger": "task",
}

# Edge type mapping
VETKA_TO_N8N_OUTPUT = {
    "structural": "main",
    "dataflow": "main",
    "temporal": "main",
    "conditional": "main",
    "parallel_fork": "main",
    "parallel_join": "main",
    "feedback": "main",
}


def detect_n8n_format(data: Dict[str, Any]) -> bool:
    """
    Detect if a JSON object is in n8n workflow format.
    n8n workflows have: nodes[] with 'type' + 'typeVersion', and connections{}.
    """
    if not isinstance(data, dict):
        return False
    nodes = data.get("nodes", [])
    if not isinstance(nodes, list):
        return False
    if len(nodes) == 0:
        return "connections" in data  # Empty n8n workflow
    # Check first node for n8n-specific fields
    first = nodes[0] if nodes else {}
    has_type_version = "typeVersion" in first
    has_n8n_type = isinstance(first.get("type", ""), str) and (
        "n8n-nodes-base" in first.get("type", "")
        or "@n8n" in first.get("type", "")
        or first.get("type", "").startswith("n8n-nodes-")
    )
    return has_type_version or has_n8n_type or "connections" in data


def n8n_to_vetka(n8n_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert n8n workflow JSON → VETKA workflow format.

    Handles:
    - Node type mapping (n8n type → VETKA type)
    - Position conversion (n8n uses [x,y] arrays or {x,y} objects)
    - Connection parsing → edge creation
    - Parameter preservation in data{} field

    Returns VETKA workflow dict ready for WorkflowStore.save().
    """
    n8n_nodes = n8n_data.get("nodes", [])
    n8n_connections = n8n_data.get("connections", {})
    n8n_name = n8n_data.get("name", "Imported n8n Workflow")

    # Build node ID map: n8n node name → VETKA node id
    node_name_to_id: Dict[str, str] = {}
    vetka_nodes: List[Dict[str, Any]] = []

    for i, n8n_node in enumerate(n8n_nodes):
        node_id = f"n{i + 1}"
        node_name = n8n_node.get("name", f"Node {i + 1}")
        n8n_type = n8n_node.get("type", "")
        node_name_to_id[node_name] = node_id

        # Map n8n type → VETKA type
        vetka_type = N8N_TO_VETKA_TYPE.get(n8n_type, "task")

        # Parse position
        pos = n8n_node.get("position", [0, 0])
        if isinstance(pos, list) and len(pos) >= 2:
            position = {"x": pos[0], "y": pos[1]}
        elif isinstance(pos, dict):
            position = {"x": pos.get("x", 0), "y": pos.get("y", 0)}
        else:
            position = {"x": i * 200, "y": 0}

        # Preserve n8n parameters + metadata
        data: Dict[str, Any] = {
            "description": f"Imported from n8n: {n8n_type}",
            "n8n_type": n8n_type,
            "n8n_type_version": n8n_node.get("typeVersion", 1),
        }
        params = n8n_node.get("parameters", {})
        if params:
            data["n8n_parameters"] = params

        vetka_nodes.append({
            "id": node_id,
            "type": vetka_type,
            "label": node_name,
            "position": position,
            "data": data,
        })

    # Parse connections → edges
    vetka_edges: List[Dict[str, Any]] = []
    edge_counter = 0

    for source_name, outputs in n8n_connections.items():
        source_id = node_name_to_id.get(source_name)
        if not source_id:
            continue

        for output_type, connections_list in outputs.items():
            # connections_list is a list of lists (output index → connections)
            if not isinstance(connections_list, list):
                continue

            for output_index, targets in enumerate(connections_list):
                if not isinstance(targets, list):
                    continue

                for target_info in targets:
                    if not isinstance(target_info, dict):
                        continue
                    target_name = target_info.get("node", "")
                    target_id = node_name_to_id.get(target_name)
                    if not target_id:
                        continue

                    edge_counter += 1

                    # Determine edge type based on source node type and output index
                    source_node_type = ""
                    for vn in vetka_nodes:
                        if vn["id"] == source_id:
                            source_node_type = vn["type"]
                            break

                    if source_node_type == "condition":
                        edge_type = "conditional"
                        label = "true" if output_index == 0 else "false"
                    elif source_node_type == "parallel":
                        edge_type = "parallel_fork"
                        label = None
                    else:
                        edge_type = "structural"
                        label = None

                    edge: Dict[str, Any] = {
                        "id": f"e{edge_counter}",
                        "source": source_id,
                        "target": target_id,
                        "type": edge_type,
                    }
                    if label:
                        edge["label"] = label

                    vetka_edges.append(edge)

    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": f"wf_{uuid.uuid4().hex[:8]}",
        "name": n8n_name,
        "description": f"Imported from n8n ({len(vetka_nodes)} nodes)",
        "nodes": vetka_nodes,
        "edges": vetka_edges,
        "metadata": {
            "created_at": now,
            "updated_at": now,
            "version": 1,
            "imported_from": "n8n",
            "original_name": n8n_name,
        },
    }


def vetka_to_n8n(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert VETKA workflow → n8n JSON format.

    Handles:
    - Node type mapping (VETKA → n8n type)
    - Position conversion
    - Edge → connection mapping
    - Original n8n parameters restoration (if available from import)

    Returns n8n-compatible workflow JSON.
    """
    vetka_nodes = workflow.get("nodes", [])
    vetka_edges = workflow.get("edges", [])
    wf_name = workflow.get("name", "Exported from VETKA")

    # Build node ID → name map and n8n nodes
    node_id_to_name: Dict[str, str] = {}
    n8n_nodes: List[Dict[str, Any]] = []

    for i, vnode in enumerate(vetka_nodes):
        node_id = vnode.get("id", f"n{i}")
        node_name = vnode.get("label", f"Node {i + 1}")
        vetka_type = vnode.get("type", "task")
        data = vnode.get("data", {})
        pos = vnode.get("position", {"x": 0, "y": 0})

        node_id_to_name[node_id] = node_name

        # Determine n8n type — prefer original if available (round-trip)
        n8n_type = data.get("n8n_type") or VETKA_TO_N8N_TYPE.get(vetka_type, "n8n-nodes-base.code")
        type_version = data.get("n8n_type_version", 1)

        # Restore original parameters if available, else create minimal ones
        parameters = data.get("n8n_parameters", {})
        if not parameters:
            parameters = _make_n8n_parameters(vetka_type, data)

        n8n_node: Dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "name": node_name,
            "type": n8n_type,
            "typeVersion": type_version,
            "position": [pos.get("x", i * 250), pos.get("y", 0)],
            "parameters": parameters,
        }

        n8n_nodes.append(n8n_node)

    # Build connections from edges
    # n8n format: {sourceNodeName: {outputType: [[{node, type, index}]]}}
    connections: Dict[str, Dict[str, List]] = {}

    for edge in vetka_edges:
        source_id = edge.get("source", "")
        target_id = edge.get("target", "")
        source_name = node_id_to_name.get(source_id)
        target_name = node_id_to_name.get(target_id)
        if not source_name or not target_name:
            continue

        edge_type = edge.get("type", "structural")
        output_type = VETKA_TO_N8N_OUTPUT.get(edge_type, "main")

        if source_name not in connections:
            connections[source_name] = {}
        if output_type not in connections[source_name]:
            connections[source_name][output_type] = [[]]

        # For conditional edges, use output index 0=true, 1=false
        output_index = 0
        if edge_type == "conditional" and edge.get("label") == "false":
            output_index = 1
            # Ensure we have enough output slots
            while len(connections[source_name][output_type]) <= output_index:
                connections[source_name][output_type].append([])

        connections[source_name][output_type][output_index].append({
            "node": target_name,
            "type": output_type,
            "index": 0,
        })

    return {
        "name": wf_name,
        "nodes": n8n_nodes,
        "connections": connections,
        "active": False,
        "settings": {
            "executionOrder": "v1",
        },
        "tags": [],
        "meta": {
            "instanceId": "vetka-export",
            "exported_from": "vetka",
            "original_id": workflow.get("id", ""),
        },
    }


def _make_n8n_parameters(vetka_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create minimal n8n parameters based on VETKA node type."""
    desc = data.get("description", "")
    if vetka_type in ("task", "subtask"):
        return {
            "jsCode": f"// {desc}\nreturn items;",
        }
    elif vetka_type == "agent":
        return {
            "url": "",
            "method": "POST",
            "options": {},
            "description": desc,
        }
    elif vetka_type == "condition":
        expr = data.get("expression", "true")
        return {
            "conditions": {
                "boolean": [{"value1": f"={{{{ {expr} }}}}"}],
            },
        }
    elif vetka_type == "transform":
        return {
            "values": {
                "string": [{"name": "result", "value": desc}],
            },
        }
    elif vetka_type == "loop":
        return {
            "batchSize": data.get("max_iterations", 10),
        }
    return {}
