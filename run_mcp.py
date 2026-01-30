#!/usr/bin/env python3
"""
VETKA MCP Runner - Sets up PYTHONPATH and runs the MCP bridge.
Use this script in OpenCode/Claude config.

Usage:
  python run_mcp.py

OpenCode config (.opencode.json):
  {
    "mcpServers": {
      "vetka": {
        "command": "python",
        "args": ["run_mcp.py"],
        "cwd": "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
      }
    }
  }
"""

import sys
import os

# Add project root to PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Now run the MCP bridge
from src.mcp.vetka_mcp_bridge import main
import asyncio

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
