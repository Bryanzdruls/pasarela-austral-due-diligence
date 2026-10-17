"""Observadores del chat: muestran lo que el sistema decidió, no lo que el modelo cuenta.

Un bloqueo llega de la decisión de los hooks de reglas; el informe y el escalamiento, del sobre que
confirma el servidor (`ok: true`). Ninguno lanza ni cambia una decisión: observar es opcional.
"""

from collections.abc import Callable
from typing import Any

from due_diligence.events import (
    CallBlocked,
    DomainEvent,
    Escalated,
    FrontFinding,
    ReportRegistered,
)
from due_diligence.rule_hooks import Hook
from due_diligence.rules import ESCALAR, INFORME, Decision, _declared_fronts, parse_envelope
from due_diligence.web.hallazgos import FRENTE_DE, resumen_de

Emit = Callable[[DomainEvent], Any]


def _short(tool: Any) -> str:
    return tool.rsplit("__", 1)[-1] if isinstance(tool, str) else ""


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _finding_from(tool: str, input_data: dict[str, Any]) -> DomainEvent | None:
    """El hallazgo de una consulta que el servidor confirmó; nada si falló o no se entiende."""
    envelope = parse_envelope(input_data.get("tool_response"))
    if envelope is None or envelope.get("ok") is not True:
        return None
    content = envelope.get("content")
    consulta = input_data.get("tool_input")
    resumen = resumen_de(tool, content, consulta) if isinstance(content, dict) else None
    if not resumen:
        return None
    metadata = envelope.get("metadata")
    sello = metadata if isinstance(metadata, dict) else {}
    return FrontFinding(
        FRENTE_DE[tool],
        resumen,
        fuente=_text(sello.get("source")),
        fecha=_text(sello.get("fetched_at")),
    )


def _event_from(input_data: dict[str, Any]) -> DomainEvent | None:
    tool = _short(input_data.get("tool_name"))
    if tool in FRENTE_DE:
        return _finding_from(tool, input_data)
    if tool not in (INFORME, ESCALAR):
        return None
    envelope = parse_envelope(input_data.get("tool_response"))
    tool_input = input_data.get("tool_input")
    if envelope is None or envelope.get("ok") is not True or not isinstance(tool_input, dict):
        return None
    content = envelope.get("content")
    if not isinstance(content, dict):
        return None
    comercio = _text(tool_input.get("comercio_id"))
    if tool == INFORME and isinstance(content.get("informe_id"), str):
        sin_cubrir = tuple(sorted(_declared_fronts(tool_input.get("cobertura"))))
        return ReportRegistered(
            content["informe_id"],
            comercio,
            _text(tool_input.get("recomendacion")),
            sin_cubrir=sin_cubrir,
        )
    if tool == ESCALAR and isinstance(content.get("escalamiento_id"), str):
        return Escalated(content["escalamiento_id"], comercio, _text(tool_input.get("causa")))
    return None


def observador_post(emit: Emit) -> Hook:
    """`PostToolUse`: publica el informe o el escalamiento que el servidor confirmó."""

    async def post_tool_use(
        input_data: dict[str, Any], tool_use_id: str | None, context: Any
    ) -> dict[str, Any]:
        try:
            event = _event_from(input_data)
            if event is not None:
                emit(event)
        except Exception:  # noqa: BLE001 - observar nunca rompe el hook
            pass
        return {}

    return post_tool_use


def observador_bloqueo(emit: Emit) -> Callable[[dict[str, Any], Decision], None]:
    """Para `on_decision`: publica cada llamada rechazada con su regla y su motivo."""

    avisadas: set[str] = set()  # llamadas ya mostradas: dos hooks pueden rechazar la misma

    def on_decision(input_data: dict[str, Any], decision: Decision) -> None:
        llamada = input_data.get("tool_use_id")
        if isinstance(llamada, str) and llamada:
            if llamada in avisadas:
                return
            avisadas.add(llamada)
        emit(
            CallBlocked(
                agente=_text(input_data.get("agent_type")) or "coordinador",
                herramienta=_short(input_data.get("tool_name")),
                regla=decision.rule or "",
                motivo=decision.reason,
            )
        )

    return on_decision
