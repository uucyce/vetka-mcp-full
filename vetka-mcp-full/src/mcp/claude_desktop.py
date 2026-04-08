"""
Claude Desktop configuration generator for VETKA MCP.

Generates claude_desktop_config.json for Claude Desktop integration.
Supports both stdio transport (recommended) and SSE transport.

Usage:
    from src.mcp.claude_desktop import generate_claude_config

    config = generate_claude_config()
    # Or with custom path
    config = generate_claude_config(project_path="/custom/path")

@status: active
@phase: 96
@depends: json, sys, pathlib
@used_by: CLI, stdio_server
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional


def get_python_path() -> str:
    """Get the Python interpreter path"""
    return sys.executable


def generate_claude_config(
    project_path: Optional[str] = None,
    server_name: str = "vetka-mcp",
    use_sse: bool = False,
    sse_url: str = "http://localhost:5005"
) -> Dict[str, Any]:
    """Generate Claude Desktop configuration

    Args:
        project_path: Path to VETKA project (auto-detected if None)
        server_name: Name for the MCP server in Claude
        use_sse: Use SSE transport instead of stdio
        sse_url: URL for SSE transport (if use_sse=True)

    Returns:
        Configuration dictionary ready for claude_desktop_config.json
    """
    if project_path is None:
        # Auto-detect project path
        project_path = str(Path(__file__).parent.parent.parent)

    project_path = str(Path(project_path).resolve())

    if use_sse:
        # SSE transport configuration
        server_config = {
            "transport": "sse",
            "url": f"{sse_url}/mcp/sse"
        }
    else:
        # Stdio transport configuration (recommended)
        python_path = get_python_path()
        stdio_server = str(Path(project_path) / "src" / "mcp" / "stdio_server.py")

        server_config = {
            "command": python_path,
            "args": [stdio_server],
            "env": {
                "VETKA_PROJECT_PATH": project_path,
                "PYTHONPATH": project_path
            }
        }

    config = {
        "mcpServers": {
            server_name: server_config
        }
    }

    return config


def save_claude_config(
    output_path: Optional[str] = None,
    **kwargs
) -> str:
    """Generate and save Claude Desktop configuration

    Args:
        output_path: Where to save config (default: project/claude_desktop_config.json)
        **kwargs: Arguments passed to generate_claude_config

    Returns:
        Path to saved configuration file
    """
    config = generate_claude_config(**kwargs)

    if output_path is None:
        project_path = kwargs.get('project_path')
        if project_path is None:
            project_path = str(Path(__file__).parent.parent.parent)
        output_path = str(Path(project_path) / "claude_desktop_config.json")

    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)

    return output_path


def get_installation_instructions() -> str:
    """Get instructions for installing VETKA MCP in Claude Desktop"""
    project_path = str(Path(__file__).parent.parent.parent.resolve())
    config = generate_claude_config(project_path=project_path)

    instructions = f"""
╔══════════════════════════════════════════════════════════════════╗
║           VETKA MCP - Claude Desktop Installation                ║
╚══════════════════════════════════════════════════════════════════╝

1. Open Claude Desktop Settings (⌘,)

2. Navigate to "Developer" → "MCP Servers"

3. Click "Edit Config" to open claude_desktop_config.json

4. Add the following configuration:

{json.dumps(config, indent=2)}

5. Restart Claude Desktop

6. Verify connection: Open a new chat and check that VETKA tools
   are available in the tools panel.

═══════════════════════════════════════════════════════════════════

Alternative: Run this command to generate config file:

    python -c "from src.mcp.claude_desktop import save_claude_config; print(save_claude_config())"

Available VETKA Tools (11 total):
  • vetka_search         - Search codebase by query
  • vetka_search_knowledge - Search knowledge base
  • vetka_get_tree       - Get project tree structure
  • vetka_get_node       - Get specific node details
  • vetka_list_files     - List files in directory
  • vetka_read_file      - Read file contents
  • vetka_edit_file      - Edit file (dry_run by default)
  • vetka_create_branch  - Create folder/branch
  • vetka_git_status     - Get git status
  • vetka_git_commit     - Commit changes (dry_run by default)
  • vetka_run_tests      - Run test file (dry_run by default)

Project Path: {project_path}
"""
    return instructions


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate Claude Desktop config for VETKA MCP")
    parser.add_argument("--save", action="store_true", help="Save config to file")
    parser.add_argument("--output", "-o", type=str, help="Output path for config")
    parser.add_argument("--sse", action="store_true", help="Use SSE transport instead of stdio")
    parser.add_argument("--url", type=str, default="http://localhost:5005", help="SSE server URL")
    parser.add_argument("--instructions", "-i", action="store_true", help="Show installation instructions")

    args = parser.parse_args()

    if args.instructions:
        print(get_installation_instructions())
    elif args.save:
        path = save_claude_config(output_path=args.output, use_sse=args.sse, sse_url=args.url)
        print(f"Configuration saved to: {path}")
    else:
        config = generate_claude_config(use_sse=args.sse, sse_url=args.url)
        print(json.dumps(config, indent=2))
