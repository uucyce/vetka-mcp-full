#!/usr/bin/env python3
"""
Generate human-readable MCP tool reference docs from inputSchema definitions.

MARKER_191.5: Schema-as-documentation.

Parses actual Python objects (not regex) from:
  - src/mcp/vetka_mcp_bridge.py    → VETKA tools (via @server.list_tools)
  - src/mcp/mycelium_mcp_server.py → MYCELIUM tools (via MYCELIUM_TOOLS)
  - src/mcp/tools/task_board_tools.py → Shared schemas (TASK_BOARD_SCHEMA)

Outputs:
  - docs/api/VETKA_MCP_REFERENCE.md
  - docs/api/MYCELIUM_MCP_REFERENCE.md

Usage:
  python3 scripts/generate_mcp_docs.py
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).parent.parent
SRC = PROJECT_ROOT / "src"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "api"


def extract_tools_from_bridge() -> list:
    """Extract Tool() definitions from vetka_mcp_bridge.py using regex on source."""
    path = SRC / "mcp" / "vetka_mcp_bridge.py"
    if not path.exists():
        print(f"  WARNING: {path} not found")
        return []

    content = path.read_text()
    tools = []

    # Match Tool( name="...", description="...", inputSchema={...} )
    # We need to find balanced braces for inputSchema
    pattern = re.compile(
        r'Tool\(\s*name\s*=\s*"([\w_]+)"\s*,\s*'
        r'description\s*=\s*("(?:[^"\\]|\\.)*"(?:\s*"(?:[^"\\]|\\.)*")*)\s*,\s*'
        r'inputSchema\s*=\s*(\{)',
        re.DOTALL
    )

    for m in pattern.finditer(content):
        name = m.group(1)
        # Parse description (may be multi-line concatenated strings)
        desc_raw = m.group(2)
        # Join multi-line string concatenation: "foo"\n  "bar" → "foobar"
        desc_parts = re.findall(r'"((?:[^"\\]|\\.)*)"', desc_raw)
        desc = "".join(desc_parts)

        # Extract balanced braces for inputSchema
        start = m.start(3)
        schema_str = _extract_balanced_braces(content, start)
        if schema_str:
            try:
                # Convert Python dict literal to JSON-compatible
                schema = eval(schema_str)  # Safe: our own schema dicts
                tools.append({"name": name, "description": desc, "schema": schema})
            except Exception as e:
                # Fallback: tool without schema details
                tools.append({"name": name, "description": desc, "schema": None, "parse_error": str(e)})
        else:
            tools.append({"name": name, "description": desc, "schema": None})

    return tools


def extract_tools_from_mycelium() -> list:
    """Extract MYCELIUM_TOOLS from mycelium_mcp_server.py."""
    path = SRC / "mcp" / "mycelium_mcp_server.py"
    if not path.exists():
        print(f"  WARNING: {path} not found")
        return []

    content = path.read_text()
    tools = []

    pattern = re.compile(
        r'Tool\(\s*name\s*=\s*"([\w_]+)"\s*,\s*'
        r'description\s*=\s*("(?:[^"\\]|\\.)*"(?:\s*"(?:[^"\\]|\\.)*")*)\s*,\s*'
        r'inputSchema\s*=\s*(\{|TASK_BOARD_SCHEMA)',
        re.DOTALL
    )

    for m in pattern.finditer(content):
        name = m.group(1)
        desc_raw = m.group(2)
        desc_parts = re.findall(r'"((?:[^"\\]|\\.)*)"', desc_raw)
        desc = "".join(desc_parts)
        schema_ref = m.group(3)

        if schema_ref == "TASK_BOARD_SCHEMA":
            # Import actual schema
            try:
                sys.path.insert(0, str(PROJECT_ROOT))
                from src.mcp.tools.task_board_tools import TASK_BOARD_SCHEMA
                tools.append({"name": name, "description": desc, "schema": TASK_BOARD_SCHEMA})
            except Exception as e:
                tools.append({"name": name, "description": desc, "schema": None, "parse_error": str(e)})
        else:
            start = m.start(3)
            schema_str = _extract_balanced_braces(content, start)
            if schema_str:
                try:
                    schema = eval(schema_str)
                    tools.append({"name": name, "description": desc, "schema": schema})
                except Exception as e:
                    tools.append({"name": name, "description": desc, "schema": None, "parse_error": str(e)})
            else:
                tools.append({"name": name, "description": desc, "schema": None})

    return tools


def _extract_balanced_braces(text: str, start: int) -> str:
    """Extract text from start position to matching closing brace."""
    depth = 0
    i = start
    while i < len(text):
        ch = text[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        elif ch == '"':
            # Skip string content
            i += 1
            while i < len(text) and text[i] != '"':
                if text[i] == '\\':
                    i += 1
                i += 1
        elif ch == "'":
            i += 1
            while i < len(text) and text[i] != "'":
                if text[i] == '\\':
                    i += 1
                i += 1
        i += 1
    return None


def generate_markdown(namespace: str, tools: list) -> str:
    """Generate Markdown reference for a list of tools."""
    lines = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines.append(f"# {namespace.upper()} MCP Tool Reference")
    lines.append("")
    lines.append(f"> Auto-generated from MCP schema definitions on {now}")
    lines.append(f"> Generator: `scripts/generate_mcp_docs.py` (MARKER_191.5)")
    lines.append(f"> Total tools: **{len(tools)}**")
    lines.append("")

    # Table of contents
    lines.append("## Table of Contents")
    lines.append("")
    for tool in sorted(tools, key=lambda t: t["name"]):
        anchor = tool["name"].replace("_", "-")
        lines.append(f"- [`{tool['name']}`](#{anchor})")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Tool details
    for tool in sorted(tools, key=lambda t: t["name"]):
        lines.append(f"## `{tool['name']}`")
        lines.append("")
        lines.append(tool["description"])
        lines.append("")

        schema = tool.get("schema")
        if not schema:
            if tool.get("parse_error"):
                lines.append(f"*Schema parse error: {tool['parse_error']}*")
            else:
                lines.append("*No schema available*")
            lines.append("")
            lines.append("---")
            lines.append("")
            continue

        props = schema.get("properties", {})
        required = set(schema.get("required", []))

        if not props:
            lines.append("*No parameters*")
            lines.append("")
            lines.append("---")
            lines.append("")
            continue

        # Parameters table
        lines.append("### Parameters")
        lines.append("")
        lines.append("| Parameter | Type | Required | Default | Description |")
        lines.append("|-----------|------|----------|---------|-------------|")

        for pname, pdef in props.items():
            ptype = pdef.get("type", "any")
            # Handle array types
            if ptype == "array":
                items_type = pdef.get("items", {}).get("type", "any")
                ptype = f"array[{items_type}]"
            elif ptype == "object":
                ptype = "object"

            is_req = "Yes" if pname in required else "No"
            default = pdef.get("default", "—")
            if default is True:
                default = "`true`"
            elif default is False:
                default = "`false`"
            elif default == "—":
                pass
            else:
                default = f"`{default}`"

            desc = pdef.get("description", "—")
            # Escape pipe chars in description
            desc = desc.replace("|", "\\|").replace("\n", " ")

            # Add enum values if present
            enum_vals = pdef.get("enum")
            if enum_vals:
                enum_str = ", ".join(f"`{v}`" for v in enum_vals)
                desc = f"{desc} Values: {enum_str}"

            # Add min/max if present
            constraints = []
            if "minimum" in pdef:
                constraints.append(f"min: {pdef['minimum']}")
            if "maximum" in pdef:
                constraints.append(f"max: {pdef['maximum']}")
            if constraints:
                desc += f" ({', '.join(constraints)})"

            lines.append(f"| `{pname}` | `{ptype}` | {is_req} | {default} | {desc} |")

        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("MCP Schema → Docs Generator (MARKER_191.5)")
    print("=" * 60)

    # Ensure output dir exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # VETKA tools
    print("\n  Scanning VETKA MCP bridge...")
    vetka_tools = extract_tools_from_bridge()
    print(f"    Found {len(vetka_tools)} tools")
    with_schema = sum(1 for t in vetka_tools if t.get("schema"))
    print(f"    With full schema: {with_schema}")

    vetka_md = generate_markdown("VETKA", vetka_tools)
    vetka_path = OUTPUT_DIR / "VETKA_MCP_REFERENCE.md"
    vetka_path.write_text(vetka_md)
    print(f"    Saved: {vetka_path}")

    # MYCELIUM tools
    print("\n  Scanning MYCELIUM MCP server...")
    mycelium_tools = extract_tools_from_mycelium()
    print(f"    Found {len(mycelium_tools)} tools")
    with_schema = sum(1 for t in mycelium_tools if t.get("schema"))
    print(f"    With full schema: {with_schema}")

    mycelium_md = generate_markdown("MYCELIUM", mycelium_tools)
    mycelium_path = OUTPUT_DIR / "MYCELIUM_MCP_REFERENCE.md"
    mycelium_path.write_text(mycelium_md)
    print(f"    Saved: {mycelium_path}")

    print(f"\n  Total: {len(vetka_tools) + len(mycelium_tools)} tools documented")
    print("=" * 60)


if __name__ == "__main__":
    main()
