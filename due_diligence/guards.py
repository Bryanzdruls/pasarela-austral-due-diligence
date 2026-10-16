"""Hook PreToolUse: garantiza el aislamiento de herramientas por rol (falla cerrado).

- Subagente de un frente: solo su herramienta de `FRONT_TOOLS`.
- Coordinador (sin `agent_type`): solo delegar con Agent/Task, solo en los cuatro frentes y de
  forma síncrona; la herramienta Agent también podría lanzar subagentes integrados con
  herramientas amplias, o en segundo plano (el resultado sería un acuse, no el JSON del frente).

Con `PASARELA_HOOK_TRACE=<ruta>` cada decisión se anota en un archivo JSONL: sirve para comprobar
en una ejecución real qué campos entrega el SDK (por ejemplo `agent_type`).
"""

import json
import os
from typing import Any

from due_diligence.agents import FRONT_TOOLS
from due_diligence.events import FrontName

DELEGATION_TOOLS = frozenset({"Agent", "Task"})
_FRONTS = {front.value for front in FrontName}


def _deny(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _decide(input_data: dict[str, Any]) -> dict[str, Any]:
    tool = input_data.get("tool_name", "")
    agent_type = input_data.get("agent_type")

    if agent_type is None:  # coordinador
        if tool in DELEGATION_TOOLS:
            tool_input = input_data.get("tool_input") or {}
            subagent = tool_input.get("subagent_type")
            if subagent not in _FRONTS:
                return _deny(
                    f"El coordinador solo puede delegar con {tool} en los frentes "
                    f"{sorted(_FRONTS)}; recibió subagent_type={subagent!r}."
                )
            if tool_input.get("run_in_background"):
                return _deny(
                    f"El coordinador no puede usar {tool} en segundo plano: necesita el "
                    "resultado del frente, no un acuse."
                )
            return {}
        return _deny(f"El coordinador no puede usar {tool}: solo delega con Agent.")

    if agent_type not in _FRONTS:
        return _deny(f"Subagente desconocido {agent_type!r}: no se le permite usar {tool}.")

    allowed = FRONT_TOOLS[FrontName(agent_type)]
    if tool == allowed:
        return {}
    return _deny(f"El subagente {agent_type} solo puede usar {allowed}; no {tool}.")


def _trace(input_data: dict[str, Any], decision: dict[str, Any]) -> None:
    path = os.environ.get("PASARELA_HOOK_TRACE")
    if not path:
        return
    row = {
        "tool_name": input_data.get("tool_name"),
        "agent_type": input_data.get("agent_type"),
        "agent_id": input_data.get("agent_id"),
        "decision": "deny" if decision else "allow",
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


async def tool_guard(input_data: dict[str, Any], tool_use_id: str | None, context: Any) -> dict:
    decision = _decide(input_data)
    _trace(input_data, decision)
    return decision
