# MARKER_106g_2_1: Cursor MCP config generator
"""
Generates Cursor IDE MCP configuration files
Supports both Kilo-Code and Roo-Cline agent setups
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class CursorAgentType(str, Enum):
    """Cursor agent types that need MCP configs"""
    KILO_CODE = "kilo_code"
    ROO_CLINE = "roo_cline"
    CUSTOM = "custom"

@dataclass
class MCPServerConfig:
    """MCP server configuration for Cursor"""
    name: str
    description: str
    command: str
    args: List[str]
    environment: Dict[str, str]
    disabled: bool = False
    alwaysAllow: List[str] = None

class CursorMCPConfigGenerator:
    """
    Generates Cursor IDE MCP configurations
    Creates config files for agent integration
    """

    def __init__(self, cursor_config_dir: str = None):
        """
        Initialize config generator

        Args:
            cursor_config_dir: Path to Cursor config directory
                              Default: ~/.cursor/config/mcp
        """
        if cursor_config_dir is None:
            home = os.path.expanduser("~")
            cursor_config_dir = os.path.join(home, ".cursor", "config", "mcp")

        self.cursor_config_dir = Path(cursor_config_dir)
        self.cursor_config_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Cursor config directory: {self.cursor_config_dir}")

    def generate_vetka_server_config(self,
                                     vetka_mcp_url: str = "http://localhost:5002",
                                     session_id: str = None) -> MCPServerConfig:
        """
        Generate VETKA MCP server configuration for Cursor

        Args:
            vetka_mcp_url: URL of VETKA MCP HTTP endpoint
            session_id: Optional session ID for agent isolation
        """
        env = {
            "VETKA_MCP_URL": vetka_mcp_url,
            "MCP_HTTP_MODE": "true",
        }

        if session_id:
            env["MCP_SESSION_ID"] = session_id

        return MCPServerConfig(
            name="vetka-mcp",
            description="VETKA Multi-Agent MCP Hub",
            command="python",
            args=[
                "-m", "src.mcp.vetka_mcp_bridge",
                "--http",
                "--port", "5002"
            ],
            environment=env,
            alwaysAllow=["vetka_tool_call", "vetka_resource_read", "vetka_resource_write"]
        )

    def generate_kilo_code_config(self) -> Dict[str, Any]:
        """
        Generate MCP configuration for Kilo-Code agent in Cursor

        Returns:
            Configuration dict for cursor settings.json
        """
        return {
            "mcp": {
                "servers": {
                    "vetka-kilo-code": {
                        "command": "python",
                        "args": [
                            "-m", "src.mcp.vetka_mcp_bridge",
                            "--http",
                            "--port", "5002",
                            "--session-id", "kilo-code-agent"
                        ],
                        "disabled": False,
                        "alwaysAllow": [
                            "vetka_tool_call",
                            "vetka_resource_read",
                            "vetka_resource_write",
                            "kilo_execute_code"
                        ],
                        "env": {
                            "VETKA_MCP_URL": "http://localhost:5002",
                            "AGENT_TYPE": "kilo_code",
                            "MCP_HTTP_MODE": "true",
                        }
                    }
                },
                "allowedHosts": ["localhost", "127.0.0.1"]
            }
        }

    def generate_roo_cline_config(self) -> Dict[str, Any]:
        """
        Generate MCP configuration for Roo-Cline agent in Cursor

        Returns:
            Configuration dict for cursor settings.json
        """
        return {
            "mcp": {
                "servers": {
                    "vetka-roo-cline": {
                        "command": "python",
                        "args": [
                            "-m", "src.mcp.vetka_mcp_bridge",
                            "--http",
                            "--port", "5002",
                            "--session-id", "roo-cline-agent"
                        ],
                        "disabled": False,
                        "alwaysAllow": [
                            "vetka_tool_call",
                            "vetka_resource_read",
                            "vetka_resource_write",
                            "roo_cline_execute"
                        ],
                        "env": {
                            "VETKA_MCP_URL": "http://localhost:5002",
                            "AGENT_TYPE": "roo_cline",
                            "MCP_HTTP_MODE": "true",
                            "ROO_CLINE_MODEL": "claude-opus-4-5"
                        }
                    }
                },
                "allowedHosts": ["localhost", "127.0.0.1"]
            }
        }

    def write_config_file(self, agent_type: CursorAgentType, config: Dict[str, Any]) -> Path:
        """
        Write MCP config file for agent type

        Args:
            agent_type: Type of Cursor agent
            config: Configuration dictionary

        Returns:
            Path to written config file
        """
        filename = f"cursor_{agent_type.value}_mcp.json"
        config_path = self.cursor_config_dir / filename

        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        logger.info(f"Wrote config: {config_path}")
        return config_path

    def generate_all_configs(self) -> Dict[str, Path]:
        """
        Generate all Cursor MCP configs in one go

        Returns:
            Dictionary mapping agent types to config file paths
        """
        results = {}

        # Kilo-Code config
        kilo_config = self.generate_kilo_code_config()
        kilo_path = self.write_config_file(CursorAgentType.KILO_CODE, kilo_config)
        results["kilo_code"] = kilo_path

        # Roo-Cline config
        roo_config = self.generate_roo_cline_config()
        roo_path = self.write_config_file(CursorAgentType.ROO_CLINE, roo_config)
        results["roo_cline"] = roo_path

        logger.info(f"Generated {len(results)} Cursor MCP configurations")
        return results

    def apply_to_cursor_settings(self,
                                settings_file: str = None,
                                agent_type: CursorAgentType = None) -> bool:
        """
        Apply MCP config to Cursor settings.json

        Args:
            settings_file: Path to Cursor settings.json
                          Default: ~/.cursor/settings.json
            agent_type: Specific agent to configure or None for all

        Returns:
            True if successful
        """
        if settings_file is None:
            home = os.path.expanduser("~")
            settings_file = os.path.join(home, ".cursor", "settings.json")

        try:
            # Load existing settings
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
            else:
                settings = {}

            # Generate and merge configs
            if agent_type == CursorAgentType.KILO_CODE or agent_type is None:
                kilo_config = self.generate_kilo_code_config()
                settings["mcp"] = {**settings.get("mcp", {}), **kilo_config["mcp"]}

            if agent_type == CursorAgentType.ROO_CLINE or agent_type is None:
                roo_config = self.generate_roo_cline_config()
                settings["mcp"] = {**settings.get("mcp", {}), **roo_config["mcp"]}

            # Write back
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)

            logger.info(f"Updated Cursor settings: {settings_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to update Cursor settings: {e}")
            return False

# MARKER_106g_2_2: Cursor config generator CLI
def main():
    """
    CLI interface for Cursor MCP config generation

    Usage:
        python cursor_config_generator.py --generate-all
        python cursor_config_generator.py --agent kilo_code --apply
        python cursor_config_generator.py --agent roo_cline --apply
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Cursor IDE MCP configurations"
    )
    parser.add_argument(
        "--generate-all",
        action="store_true",
        help="Generate all agent configs"
    )
    parser.add_argument(
        "--agent",
        type=str,
        choices=["kilo_code", "roo_cline"],
        help="Specific agent to configure"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply config to Cursor settings.json"
    )
    parser.add_argument(
        "--cursor-config-dir",
        type=str,
        help="Cursor config directory"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)

    # Initialize generator
    generator = CursorMCPConfigGenerator(args.cursor_config_dir)

    if args.generate_all:
        results = generator.generate_all_configs()
        print(f"Generated {len(results)} configs:")
        for agent, path in results.items():
            print(f"  - {agent}: {path}")

    if args.apply:
        agent_type = None
        if args.agent:
            agent_type = CursorAgentType[args.agent.upper()]

        success = generator.apply_to_cursor_settings(agent_type=agent_type)
        if success:
            print(f"Applied MCP config to Cursor settings")
        else:
            print("Failed to apply config")
            exit(1)

if __name__ == "__main__":
    main()
