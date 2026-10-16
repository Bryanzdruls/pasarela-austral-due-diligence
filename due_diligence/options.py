"""Construcción de las opciones del Agent SDK para el coordinador."""

import os
import sys
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, HookMatcher

from due_diligence.agents import build_agents
from due_diligence.guards import tool_guard

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_NAME = "pasarela-fuentes"
_PASSTHROUGH_ENV = ("PASARELA_FAULTS", "PASARELA_RUNTIME_DIR")


def _mcp_server_config() -> dict:
    env = {"PYTHONPATH": str(REPO_ROOT)}
    for name in _PASSTHROUGH_ENV:
        if os.environ.get(name):
            env[name] = os.environ[name]
    # McpStdioServerConfig no admite `cwd`: el módulo se hace importable con PYTHONPATH.
    return {
        "type": "stdio",
        "command": sys.executable,
        "args": ["-m", "mcp_server"],
        "env": env,
    }


def build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        agents=build_agents(),
        tools=["Agent"],  # restringe el conjunto: el coordinador solo delega
        allowed_tools=["Agent"],  # solo auto-aprueba; no restringe por sí solo
        mcp_servers={SERVER_NAME: _mcp_server_config()},
        setting_sources=[],  # no heredar la configuración del proyecto de desarrollo
        hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[tool_guard])]},
        cwd=str(REPO_ROOT),
        # Sin max_turns: el ciclo termina por la razón de parada del modelo (FR-008).
    )
