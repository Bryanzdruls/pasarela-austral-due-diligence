"""Hook PreToolUse: garantiza el aislamiento de herramientas por rol (falla cerrado).

- Subagente de un frente: solo su herramienta de `FRONT_TOOLS`.
- Coordinador (sin `agent_type`): solo delegar con Agent/Task y solo en los cuatro frentes;
  la herramienta Agent también podría lanzar subagentes integrados con herramientas amplias.
"""

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


async def tool_guard(input_data: dict[str, Any], tool_use_id: str | None, context: Any) -> dict:
    tool = input_data.get("tool_name", "")
    agent_type = input_data.get("agent_type")

    if agent_type is None:  # coordinador
        if tool in DELEGATION_TOOLS:
            subagent = (input_data.get("tool_input") or {}).get("subagent_type")
            if subagent in _FRONTS:
                return {}
            return _deny(
                f"El coordinador solo puede delegar con {tool} en los frentes {sorted(_FRONTS)}; "
                f"recibió subagent_type={subagent!r}."
            )
        return _deny(f"El coordinador no puede usar {tool}: solo delega con Agent.")

    if agent_type not in _FRONTS:
        return _deny(f"Subagente desconocido {agent_type!r}: no se le permite usar {tool}.")

    allowed = FRONT_TOOLS[FrontName(agent_type)]
    if tool == allowed:
        return {}
    return _deny(f"El subagente {agent_type} solo puede usar {allowed}; no {tool}.")
