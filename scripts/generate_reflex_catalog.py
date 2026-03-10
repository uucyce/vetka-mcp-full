#!/usr/bin/env python3
"""
Generate REFLEX tool catalog by scanning the codebase.

MARKER_172.P1.CATALOG

Scans:
  - src/tools/fc_loop.py         → PIPELINE_CODER_TOOLS
  - src/agents/tools.py          → AGENT_TOOL_PERMISSIONS + registry
  - src/mcp/vetka_mcp_bridge.py  → MCP VETKA tools
  - src/mcp/mycelium_mcp_server.py → MCP MYCELIUM tools
  - src/api/routes/cut_routes.py → CUT endpoints

Outputs:
  - data/reflex/tool_catalog.json

Usage:
  python3 scripts/generate_reflex_catalog.py
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).parent.parent
SRC = PROJECT_ROOT / "src"
OUTPUT = PROJECT_ROOT / "data" / "reflex" / "tool_catalog.json"


def scan_pipeline_coder_tools() -> list:
    """Extract PIPELINE_CODER_TOOLS from fc_loop.py."""
    path = SRC / "tools" / "fc_loop.py"
    tools = []
    if not path.exists():
        return tools

    content = path.read_text()
    match = re.search(r'PIPELINE_CODER_TOOLS\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if match:
        block = match.group(1)
        for name_match in re.finditer(r'"([\w_]+)"', block):
            name = name_match.group(1)
            tools.append({
                "tool_id": name,
                "namespace": "vetka",
                "kind": _infer_kind(name),
                "description": f"Pipeline coder tool: {name}",
                "intent_tags": _infer_intent_tags(name),
                "trigger_patterns": {
                    "file_types": ["*"],
                    "phase_types": ["fix", "build", "research"],
                    "keywords": _infer_keywords(name),
                },
                "cost": {"latency_ms": 200, "tokens": 0, "risk_level": "read_only"},
                "permission": "READ",
                "roles": ["coder", "Dev"],
                "deprecated_aliases": [],
                "active": True,
                "source": "fc_loop.py:PIPELINE_CODER_TOOLS",
            })
    return tools


def scan_agent_tool_permissions() -> dict:
    """Extract AGENT_TOOL_PERMISSIONS from tools.py → role→tools mapping."""
    path = SRC / "agents" / "tools.py"
    if not path.exists():
        return {}

    content = path.read_text()
    # Find the AGENT_TOOL_PERMISSIONS dict
    match = re.search(
        r'AGENT_TOOL_PERMISSIONS\s*:\s*Dict\[str,\s*List\[str\]\]\s*=\s*\{(.*?)\n\}',
        content, re.DOTALL
    )
    if not match:
        return {}

    block = match.group(1)
    roles_map = {}

    # Parse role blocks: "RoleName": [...]
    role_pattern = re.compile(r'"(\w+)"\s*:\s*\[(.*?)\]', re.DOTALL)
    for role_match in role_pattern.finditer(block):
        role_name = role_match.group(1)
        tools_block = role_match.group(2)
        tool_names = re.findall(r'"([\w_]+)"', tools_block)
        roles_map[role_name] = tool_names

    return roles_map


def scan_mcp_vetka_tools() -> list:
    """Extract tool registrations from vetka_mcp_bridge.py."""
    path = SRC / "mcp" / "vetka_mcp_bridge.py"
    tools = []
    if not path.exists():
        return tools

    content = path.read_text()
    seen_names = set()

    # Pattern 1: Tool( name="vetka_...", description="..." )
    pattern1 = re.compile(
        r'name\s*=\s*"(vetka_\w+)"\s*,\s*description\s*=\s*"([^"]*)"',
        re.DOTALL
    )
    for m in pattern1.finditer(content):
        name, desc = m.group(1), m.group(2)
        seen_names.add(name)
        tools.append(_make_vetka_tool(name, desc))

    # Pattern 2: elif name == "vetka_..." (handler-only tools without Tool() registration)
    pattern2 = re.compile(r'elif\s+name\s*==\s*"(vetka_\w+)"')
    for m in pattern2.finditer(content):
        name = m.group(1)
        if name not in seen_names:
            seen_names.add(name)
            tools.append(_make_vetka_tool(name, f"VETKA tool: {name}"))

    return tools


def _make_vetka_tool(name: str, desc: str) -> dict:
    """Create a vetka tool entry."""
    return {
        "tool_id": name,
        "namespace": "vetka",
        "kind": _infer_kind(name),
        "description": desc[:120],
        "intent_tags": _infer_intent_tags(name),
        "trigger_patterns": {
            "file_types": ["*"],
            "phase_types": _infer_phase_types(name),
            "keywords": _infer_keywords(name),
        },
        "cost": _infer_cost(name),
        "permission": _infer_permission(name),
        "roles": [],
        "deprecated_aliases": [],
        "active": True,
        "source": "vetka_mcp_bridge.py",
    }


def scan_mcp_mycelium_tools() -> list:
    """Extract tool registrations from mycelium_mcp_server.py."""
    path = SRC / "mcp" / "mycelium_mcp_server.py"
    tools = []
    if not path.exists():
        return tools

    content = path.read_text()
    pattern = re.compile(
        r'Tool\(\s*name\s*=\s*"(mycelium_\w+)"\s*,\s*description\s*=\s*"([^"]*)"',
        re.DOTALL
    )
    for m in pattern.finditer(content):
        name, desc = m.group(1), m.group(2)
        tools.append({
            "tool_id": name,
            "namespace": "mycelium",
            "kind": _infer_kind(name),
            "description": desc[:120],
            "intent_tags": _infer_intent_tags(name),
            "trigger_patterns": {
                "file_types": ["*"],
                "phase_types": ["*"],
                "keywords": _infer_keywords(name),
            },
            "cost": {"latency_ms": 500, "tokens": 0, "risk_level": "execute"},
            "permission": "EXECUTE",
            "roles": ["all"],
            "deprecated_aliases": [],
            "active": True,
            "source": "mycelium_mcp_server.py",
        })
    return tools


def scan_internal_tools() -> list:
    """Extract tool definitions from src/agents/tools.py registry."""
    path = SRC / "agents" / "tools.py"
    tools = []
    if not path.exists():
        return tools

    content = path.read_text()
    # Match ToolDefinition( name="...", description="...", ... )
    pattern = re.compile(
        r'ToolDefinition\(\s*name\s*=\s*"([\w_]+)"\s*,\s*description\s*=\s*"([^"]*)".*?'
        r'permission_level\s*=\s*PermissionLevel\.(\w+)',
        re.DOTALL
    )
    for m in pattern.finditer(content):
        name, desc, perm = m.group(1), m.group(2), m.group(3)
        tools.append({
            "tool_id": name,
            "namespace": "internal",
            "kind": _infer_kind(name),
            "description": desc[:120],
            "intent_tags": _infer_intent_tags(name),
            "trigger_patterns": {
                "file_types": ["*"],
                "phase_types": _infer_phase_types(name),
                "keywords": _infer_keywords(name),
            },
            "cost": _infer_cost(name),
            "permission": perm.upper(),
            "roles": [],  # Will be filled from AGENT_TOOL_PERMISSIONS
            "deprecated_aliases": [],
            "active": True,
            "source": "agents/tools.py",
        })
    return tools


def scan_cut_endpoints() -> list:
    """Extract CUT mode API endpoints as tools."""
    path = SRC / "api" / "routes" / "cut_routes.py"
    tools = []
    if not path.exists():
        return tools

    content = path.read_text()
    # Match @router.post("/path") or @router.get("/path")
    pattern = re.compile(r'@router\.(post|get|put|patch|delete)\(\s*"(/[^"]+)"')
    for m in pattern.finditer(content):
        method, endpoint = m.group(1).upper(), m.group(2)
        # Create a tool_id from the endpoint
        tool_id = "cut_" + endpoint.strip("/").replace("/", "_").replace("{", "").replace("}", "")
        tools.append({
            "tool_id": tool_id,
            "namespace": "cut",
            "kind": "media",
            "description": f"CUT API: {method} {endpoint}",
            "intent_tags": ["video", "edit", "timeline", "cut", "media", "montage"],
            "trigger_patterns": {
                "file_types": [".mp4", ".mov", ".avi", ".mkv", ".wav", ".mp3"],
                "phase_types": ["build"],
                "keywords": ["video", "cut", "timeline", "scene", "edit", "montage"],
            },
            "cost": {"latency_ms": 300, "tokens": 0, "risk_level": "write"},
            "permission": "WRITE",
            "roles": ["coder", "Dev"],
            "deprecated_aliases": [],
            "active": True,
            "source": "cut_routes.py",
        })
    return tools


# ─── Inference helpers ───────────────────────────────────────────────

def _infer_kind(name: str) -> str:
    """Infer tool kind from name."""
    name_lower = name.lower()
    if any(k in name_lower for k in ["search", "find", "list", "get_tree"]):
        return "search"
    if any(k in name_lower for k in ["read", "edit", "write"]):
        return "file_op"
    if any(k in name_lower for k in ["pipeline", "task", "dispatch", "workflow", "heartbeat"]):
        return "orchestration"
    if any(k in name_lower for k in ["cam", "surprise", "elision", "memory", "engram", "stm"]):
        return "memory"
    if any(k in name_lower for k in ["cut", "media", "player", "video"]):
        return "media"
    if any(k in name_lower for k in ["git", "commit", "test", "health"]):
        return "system"
    if any(k in name_lower for k in ["session", "context", "dag", "knowledge"]):
        return "context"
    if any(k in name_lower for k in ["camera", "viewport"]):
        return "visualization"
    if any(k in name_lower for k in ["artifact", "approve", "reject"]):
        return "artifact"
    if any(k in name_lower for k in ["model", "call"]):
        return "llm"
    if any(k in name_lower for k in ["api_key", "key"]):
        return "keys"
    if any(k in name_lower for k in ["arc", "suggest"]):
        return "reasoning"
    return "other"


def _infer_intent_tags(name: str) -> list:
    """Infer intent tags from tool name."""
    tags = []
    name_lower = name.lower()

    tag_map = {
        "search": ["find", "locate", "query", "discover"],
        "semantic": ["concept", "meaning", "similar", "vector"],
        "read": ["view", "inspect", "content", "examine"],
        "edit": ["modify", "change", "update", "patch"],
        "write": ["create", "generate", "produce"],
        "list": ["browse", "enumerate", "directory"],
        "git": ["version", "commit", "history", "branch"],
        "test": ["verify", "validate", "check", "quality"],
        "pipeline": ["execute", "run", "orchestrate", "automate"],
        "task": ["plan", "track", "manage", "assign"],
        "artifact": ["output", "result", "deliverable"],
        "camera": ["view", "focus", "navigate", "3d"],
        "session": ["connect", "initialize", "state"],
        "health": ["status", "diagnostic", "monitor"],
        "surprise": ["novelty", "anomaly", "unexpected"],
        "elision": ["compress", "compact", "reduce"],
        "cut": ["video", "edit", "timeline", "montage"],
        "model": ["llm", "ai", "generate", "infer"],
        "arc": ["reason", "abstract", "hypothesis"],
        "key": ["auth", "credential", "api"],
    }

    for keyword, intent in tag_map.items():
        if keyword in name_lower:
            tags.extend(intent)

    return list(set(tags)) if tags else ["general"]


def _infer_keywords(name: str) -> list:
    """Infer trigger keywords from tool name."""
    parts = name.replace("vetka_", "").replace("mycelium_", "").replace("cut_", "").split("_")
    return [p for p in parts if len(p) > 2]


def _infer_phase_types(name: str) -> list:
    """Infer relevant phase types."""
    name_lower = name.lower()
    if any(k in name_lower for k in ["search", "read", "list", "semantic"]):
        return ["research", "fix", "build"]
    if any(k in name_lower for k in ["edit", "write", "commit"]):
        return ["fix", "build"]
    if any(k in name_lower for k in ["test", "health"]):
        return ["fix"]
    return ["*"]


def _infer_permission(name: str) -> str:
    """Infer permission level."""
    name_lower = name.lower()
    if any(k in name_lower for k in ["edit", "write", "commit"]):
        return "WRITE"
    if any(k in name_lower for k in ["execute", "pipeline", "dispatch"]):
        return "EXECUTE"
    if any(k in name_lower for k in ["call_model"]):
        return "EXTERNAL"
    return "READ"


def _infer_cost(name: str) -> dict:
    """Infer cost metadata."""
    name_lower = name.lower()
    if "call_model" in name_lower:
        return {"latency_ms": 2000, "tokens": 500, "risk_level": "external"}
    if any(k in name_lower for k in ["pipeline", "workflow", "execute"]):
        return {"latency_ms": 5000, "tokens": 0, "risk_level": "execute"}
    if any(k in name_lower for k in ["edit", "write", "commit"]):
        return {"latency_ms": 300, "tokens": 0, "risk_level": "write"}
    if any(k in name_lower for k in ["search", "semantic"]):
        return {"latency_ms": 200, "tokens": 0, "risk_level": "read_only"}
    return {"latency_ms": 100, "tokens": 0, "risk_level": "read_only"}


# ─── Merge and deduplicate ───────────────────────────────────────────

def merge_tools(all_sources: list, roles_map: dict) -> list:
    """Merge tools from all sources, deduplicate by tool_id, enrich with roles."""
    seen = {}
    for tool in all_sources:
        tid = tool["tool_id"]
        if tid in seen:
            # Merge: prefer MCP source over internal, keep richer metadata
            existing = seen[tid]
            # Merge roles
            existing_roles = set(existing.get("roles", []))
            new_roles = set(tool.get("roles", []))
            existing["roles"] = list(existing_roles | new_roles)
            # Prefer longer description
            if len(tool.get("description", "")) > len(existing.get("description", "")):
                existing["description"] = tool["description"]
            # Merge sources
            existing["source"] = existing.get("source", "") + " + " + tool.get("source", "")
        else:
            seen[tid] = tool

    # Enrich with role information from AGENT_TOOL_PERMISSIONS
    for role_name, tool_names in roles_map.items():
        for tname in tool_names:
            if tname in seen:
                roles = set(seen[tname].get("roles", []))
                roles.add(role_name)
                seen[tname]["roles"] = list(roles)

    return list(seen.values())


# ─── Main ────────────────────────────────────────────────────────────

def generate_catalog() -> dict:
    """Generate the full REFLEX tool catalog."""
    print("=" * 60)
    print("REFLEX Catalog Generator")
    print("=" * 60)

    # Scan all sources
    print("  Scanning PIPELINE_CODER_TOOLS...")
    coder_tools = scan_pipeline_coder_tools()
    print(f"    Found {len(coder_tools)} coder tools")

    print("  Scanning AGENT_TOOL_PERMISSIONS...")
    roles_map = scan_agent_tool_permissions()
    print(f"    Found {len(roles_map)} roles: {list(roles_map.keys())}")

    print("  Scanning internal tool registry...")
    internal_tools = scan_internal_tools()
    print(f"    Found {len(internal_tools)} internal tools")

    print("  Scanning MCP VETKA tools...")
    vetka_tools = scan_mcp_vetka_tools()
    print(f"    Found {len(vetka_tools)} VETKA MCP tools")

    print("  Scanning MCP MYCELIUM tools...")
    mycelium_tools = scan_mcp_mycelium_tools()
    print(f"    Found {len(mycelium_tools)} MYCELIUM tools")

    print("  Scanning CUT endpoints...")
    cut_tools = scan_cut_endpoints()
    print(f"    Found {len(cut_tools)} CUT endpoints")

    # Merge and deduplicate
    all_tools = coder_tools + internal_tools + vetka_tools + mycelium_tools + cut_tools
    print(f"\n  Total raw: {len(all_tools)}")

    merged = merge_tools(all_tools, roles_map)
    print(f"  After dedup+merge: {len(merged)}")

    # Build catalog
    catalog = {
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/generate_reflex_catalog.py",
        "marker": "MARKER_172.P1.CATALOG",
        "stats": {
            "total_tools": len(merged),
            "by_namespace": {},
            "by_kind": {},
        },
        "deprecated_aliases": {
            # Phase 129: VETKA → MYCELIUM migration
            "vetka_task_board": "mycelium_task_board",
            "vetka_task_dispatch": "mycelium_task_dispatch",
            "vetka_task_import": "mycelium_task_import",
            "vetka_mycelium_pipeline": "mycelium_pipeline",
            "vetka_heartbeat_tick": "mycelium_heartbeat_tick",
            "vetka_heartbeat_status": "mycelium_heartbeat_status",
            "search_semantic": "vetka_search_semantic",
            "camera_focus": "vetka_camera_focus",
            "create_artifact": "vetka_edit_artifact",
        },
        "tools": merged,
    }

    # Compute stats
    for tool in merged:
        ns = tool.get("namespace", "unknown")
        catalog["stats"]["by_namespace"][ns] = catalog["stats"]["by_namespace"].get(ns, 0) + 1
        kind = tool.get("kind", "unknown")
        catalog["stats"]["by_kind"][kind] = catalog["stats"]["by_kind"].get(kind, 0) + 1

    return catalog


def main():
    catalog = generate_catalog()

    # Ensure output directory exists
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT, "w") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"\n  Saved: {OUTPUT}")
    print(f"  Tools: {catalog['stats']['total_tools']}")
    print(f"  By namespace: {json.dumps(catalog['stats']['by_namespace'])}")
    print(f"  By kind: {json.dumps(catalog['stats']['by_kind'])}")
    print("=" * 60)


if __name__ == "__main__":
    main()
