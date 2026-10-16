"""Construcción de las opciones del Agent SDK para el coordinador."""

import os
import sys
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, HookMatcher

from due_diligence.agents import FRONT_TOOLS, OUTPUT_TOOLS, build_agents
from due_diligence.guards import tool_guard
from due_diligence.prompts import COORDINATOR_PROMPT
from due_diligence.rule_hooks import (
    make_post_tool_use,
    make_pre_tool_use,
    make_stop,
    make_user_prompt_submit,
)
from due_diligence.rules import CaseBook

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


def _hooks(book: CaseBook) -> dict:
    """Aislamiento por rol y reglas de negocio 1 a 3, todos sobre el mismo `CaseBook`."""

    def everywhere(*hooks):  # sin filtro: aplica a todas las herramientas
        return [HookMatcher(matcher=None, hooks=list(hooks))]

    return {
        "PreToolUse": everywhere(tool_guard, make_pre_tool_use(book)),
        "PostToolUse": everywhere(make_post_tool_use(book)),
        "UserPromptSubmit": everywhere(make_user_prompt_submit(book)),
        "Stop": everywhere(make_stop(book)),
    }


def build_options(book: CaseBook | None = None) -> ClaudeAgentOptions:
    book = book if book is not None else CaseBook()
    return ClaudeAgentOptions(
        system_prompt=COORDINATOR_PROMPT,
        agents=build_agents(),
        tools=["Agent"],  # restringe el conjunto de herramientas integradas: solo delegar
        # allowed_tools solo auto-aprueba (no restringe). Las herramientas de frente se
        # pre-aprueban para que los subagentes puedan usarlas; el hook PreToolUse (deny gana
        # a allow) impide que el coordinador o un subagente ajeno las use.
        allowed_tools=["Agent", *FRONT_TOOLS.values(), *OUTPUT_TOOLS],
        mcp_servers={SERVER_NAME: _mcp_server_config()},
        setting_sources=[],  # no heredar la configuración del proyecto de desarrollo
        hooks=_hooks(book),
        cwd=str(REPO_ROOT),
        # Sin esto la CLI lanza los subagentes en segundo plano y el coordinador recibe un acuse.
        env={"CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1"},
        # Sin max_turns: el ciclo termina por la razón de parada del modelo (FR-008).
    )
