"""Hooks del SDK que hacen cumplir las reglas de negocio 1 a 3 (ticket #3).

Capa fina sobre `CaseBook`: parsea la entrada del SDK, consulta las decisiones puras de `rules.py` y
devuelve la forma de respuesta del SDK. Falla cerrado: una excepción en un hook que bloquea produce
una denegación, y un error al observar un resultado nunca se convierte en un permiso.

Con `PASARELA_HOOK_TRACE=<ruta>` cada decisión de regla se anota (con su regla) en el mismo archivo
JSONL que usa el guard de aislamiento.
"""

import json
import os
from collections.abc import Awaitable, Callable
from typing import Any

from due_diligence.guards import _deny
from due_diligence.rules import ESCALAR, INFORME, LISTAS, CaseBook, Decision

Hook = Callable[[dict[str, Any], str | None, Any], Awaitable[dict[str, Any]]]

# Herramientas cuyo uso deciden las reglas (el resto lo decide el guard de aislamiento).
_GOVERNED = {LISTAS: "check_listas", INFORME: "check_informe", ESCALAR: "check_escalar"}


def _short_name(tool: Any) -> str:
    return tool.rsplit("__", 1)[-1] if isinstance(tool, str) else ""


def _trace(input_data: dict[str, Any], decision: Decision) -> None:
    path = os.environ.get("PASARELA_HOOK_TRACE")
    if not path:
        return
    row = {
        "tool_name": input_data.get("tool_name"),
        "agent_type": input_data.get("agent_type"),
        "agent_id": input_data.get("agent_id"),
        "decision": "allow" if decision.allowed else "deny",
        "rule": decision.rule,
    }
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def make_pre_tool_use(book: CaseBook) -> Hook:
    """`PreToolUse`: aplica las reglas a las herramientas que gobiernan."""

    async def pre_tool_use(
        input_data: dict[str, Any], tool_use_id: str | None, context: Any
    ) -> dict[str, Any]:
        try:
            check = _GOVERNED.get(_short_name(input_data.get("tool_name")))
            if check is None:
                return {}
            decision: Decision = getattr(book, check)(input_data.get("tool_input"))
            _trace(input_data, decision)
            return {} if decision.allowed else _deny(decision.reason)
        except Exception as exc:  # noqa: BLE001 - falla cerrado: ante un error, se deniega
            return _deny(
                f"Una regla de negocio no pudo evaluarse ({type(exc).__name__}: {exc}). "
                "Se deniega la acción por seguridad."
            )

    return pre_tool_use


def make_post_tool_use(book: CaseBook) -> Hook:
    """`PostToolUse`: observa lo que devolvió cada fuente. Nunca lanza ni bloquea."""

    async def post_tool_use(
        input_data: dict[str, Any], tool_use_id: str | None, context: Any
    ) -> dict[str, Any]:
        try:
            book.observe(
                input_data.get("tool_name"),
                input_data.get("tool_input"),
                input_data.get("tool_response"),
            )
        except Exception:  # noqa: BLE001 - no registrar es lo seguro
            pass
        return {}

    return post_tool_use


def make_user_prompt_submit(book: CaseBook) -> Hook:
    """`UserPromptSubmit`: el texto del analista es la evidencia de la categoría declarada."""

    async def user_prompt_submit(
        input_data: dict[str, Any], tool_use_id: str | None, context: Any
    ) -> dict[str, Any]:
        try:
            book.start_request(input_data.get("prompt"))
        except Exception:  # noqa: BLE001 - no registrar la solicitud nunca bloquea al analista
            pass
        return {}

    return user_prompt_submit


def make_stop(book: CaseBook) -> Hook:
    """`Stop`: exige escalar antes de cerrar la respuesta si la regla 2 o la 3 aplican (D12).

    La exigencia se hace una sola vez: con `stop_hook_active` verdadero (ya se pidió) deja cerrar,
    para no entrar en un bucle. Un error interno tampoco atrapa la conversación.
    """

    async def stop(
        input_data: dict[str, Any], tool_use_id: str | None, context: Any
    ) -> dict[str, Any]:
        try:
            if input_data.get("stop_hook_active"):
                return {}
            pending = book.pending_escalations()
            if not pending:
                return {}
            return {
                "decision": "block",
                "reason": (
                    "Antes de terminar: la regla 2 o la 3 aplican a "
                    + ", ".join(pending)
                    + " y el caso no fue escalado. Escala el caso a un oficial de cumplimiento con "
                    "`escalar_a_cumplimiento` (comercio_id, hallazgos por frente con sus fuentes, "
                    "cobertura, causa y acción recomendada) y después da la respuesta."
                ),
            }
        except Exception:  # noqa: BLE001 - un fallo aquí no debe dejar la conversación atrapada
            return {}

    return stop
