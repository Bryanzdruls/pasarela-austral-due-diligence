"""Tipos de dominio del coordinador: frentes, resultados de frente y eventos."""

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from mcp_server.tools import listas, noticias, registro, riesgo


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


class FrontName(StrEnum):
    REGISTRO_MERCANTIL = "registro_mercantil"
    LISTAS_RESTRICTIVAS = "listas_restrictivas"
    NOTICIAS = "noticias"
    RIESGO_CATEGORIA = "riesgo_categoria"


class FrontStatus(StrEnum):
    COMPLETO = "completo"
    # El subagente reportó un error estructurado de su fuente (ticket #4): informa al coordinador
    # y al chat; que el frente cuente como sin cubrir lo decide el CaseBook con lo que devolvió el
    # servidor, no esta respuesta.
    FALLIDO = "fallido"
    NO_ESTRUCTURADO = "no_estructurado"
    NO_COMPLETADO = "no_completado"


# La fuente que cada frente debe declarar en `metadatos.fuente`: la misma constante que usa el
# servidor MCP en su sobre de respuesta (una sola fuente de verdad).
EXPECTED_SOURCES: dict[FrontName, str] = {
    FrontName.REGISTRO_MERCANTIL: registro.SOURCE,
    FrontName.LISTAS_RESTRICTIVAS: listas.SOURCE,
    FrontName.NOTICIAS: noticias.SOURCE,
    FrontName.RIESGO_CATEGORIA: riesgo.SOURCE,
}

_META_KEYS = ("fuente", "fecha")


@dataclass(frozen=True)
class FrontResult:
    """Resultado de un frente: contenido hallado separado de sus metadatos."""

    frente: FrontName
    contenido: dict[str, Any]
    metadatos: dict[str, str]  # {"fuente": ..., "fecha": ...}, obligatorios
    estado: FrontStatus


@dataclass(frozen=True)
class SubagentStarted:
    frente: FrontName
    tool_use_id: str
    encargo: str
    timestamp: str = field(default_factory=_now)


@dataclass(frozen=True)
class SubagentFinished:
    frente: FrontName
    result: FrontResult | None
    timestamp: str = field(default_factory=_now)


@dataclass(frozen=True)
class CoordinatorText:
    text: str
    timestamp: str = field(default_factory=_now)


@dataclass(frozen=True)
class RunFinished:
    subtype: str
    stop_reason: str | None
    terminal_reason: str | None
    timestamp: str = field(default_factory=_now)


@dataclass(frozen=True)
class CallBlocked:
    """Una llamada que un hook de reglas o de aislamiento rechazó (ticket #7, para el chat)."""

    agente: str
    herramienta: str
    regla: str
    motivo: str
    timestamp: str = field(default_factory=_now)


@dataclass(frozen=True)
class ReportRegistered:
    """El servidor confirmó el registro de un informe (`ok: true`)."""

    informe_id: str
    comercio_id: str
    recomendacion: str
    timestamp: str = field(default_factory=_now)
    sin_cubrir: tuple[str, ...] = ()  # frentes que el informe declara sin cubrir


@dataclass(frozen=True)
class Escalated:
    """El servidor confirmó un escalamiento a cumplimiento (`ok: true`)."""

    escalamiento_id: str
    comercio_id: str
    causa: str
    timestamp: str = field(default_factory=_now)


@dataclass(frozen=True)
class FrontFinding:
    """Lo que una fuente devolvió en una consulta que el servidor confirmó (`ok: true`).

    Lo redacta el sistema a partir del sobre del servidor, no el modelo (ticket #7, para el chat).
    """

    frente: FrontName
    resumen: str
    timestamp: str = field(default_factory=_now)


DomainEvent = (
    SubagentStarted
    | SubagentFinished
    | CoordinatorText
    | RunFinished
    | CallBlocked
    | ReportRegistered
    | Escalated
    | FrontFinding
)

_FENCED_ANYWHERE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)
_DELEGATION_TOOLS = ("Agent", "Task")


def _result_texts(content: Any) -> list[str]:
    """Textos del resultado de la herramienta: cada bloque por separado y todos unidos."""
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        parts = [
            p["text"] for p in content if isinstance(p, dict) and isinstance(p.get("text"), str)
        ]
        return [*parts, "".join(parts)] if len(parts) > 1 else parts
    return [""]


def _json_candidates(raw: str) -> list[str]:
    """Posibles textos JSON dentro de la respuesta: completa, con valla de código o entre llaves."""
    candidates = [raw.strip()]
    fenced = _FENCED_ANYWHERE.search(raw)
    if fenced:
        candidates.append(fenced.group(1).strip())
    first, last = raw.find("{"), raw.rfind("}")
    if 0 <= first < last:
        candidates.append(raw[first : last + 1])
    return candidates


def _is_iso_date(value: str) -> bool:
    try:
        datetime.fromisoformat(value)
    except ValueError:
        return False
    return True


def _valid_metadatos(frente: FrontName, metadatos: Any) -> dict[str, str] | None:
    """Fuente propia del frente y fecha ISO; None si no cumplen."""
    if not isinstance(metadatos, dict):
        return None
    if not all(isinstance(metadatos.get(k), str) and metadatos[k].strip() for k in _META_KEYS):
        return None
    if metadatos["fuente"] != EXPECTED_SOURCES[frente] or not _is_iso_date(metadatos["fecha"]):
        return None
    return {k: metadatos[k] for k in _META_KEYS}


def _validated(frente: FrontName, data: Any) -> FrontResult | None:
    if not isinstance(data, dict):
        return None
    contenido = data.get("contenido")
    metadatos = _valid_metadatos(frente, data.get("metadatos"))
    if not (isinstance(contenido, dict) and contenido and metadatos):
        return None
    return FrontResult(frente, contenido, metadatos, FrontStatus.COMPLETO)


def _validated_error(frente: FrontName, data: Any) -> FrontResult | None:
    """Error estructurado de un subagente: `{"estado": "error", "frente", "reintentable", ...}`."""
    if not isinstance(data, dict) or data.get("estado") != "error":
        return None
    reintentable, obtenido = data.get("reintentable", False), data.get("obtenido", {})
    metadatos = _valid_metadatos(frente, data.get("metadatos"))
    if data.get("frente") != frente.value or not metadatos:
        return None
    if not isinstance(reintentable, bool) or not isinstance(obtenido, dict):
        return None
    error: dict[str, Any] = {"reintentable": reintentable, "obtenido": obtenido}
    motivo = data.get("motivo")
    if isinstance(motivo, str) and motivo.strip():
        error["motivo"] = motivo.strip()
    return FrontResult(frente, {"error": error}, metadatos, FrontStatus.FALLIDO)


def parse_front_result(frente: FrontName, raw: str) -> FrontResult:
    """Convierte la respuesta de un subagente en FrontResult (completo, fallido o no estructurado).

    Es tolerante con la forma (texto antes del JSON, valla de código) y estricta con el fondo:
    contenido no vacío, fuente propia del frente y fecha ISO válida. Nunca da por buena una
    respuesta mal formada.
    """
    for candidate in _json_candidates(raw):
        try:
            data = json.loads(candidate)
            result = _validated_error(frente, data) or _validated(frente, data)
        except (ValueError, TypeError):
            continue
        if result is not None:
            return result
    return FrontResult(frente, {"texto_sin_estructura": raw}, {}, FrontStatus.NO_ESTRUCTURADO)


class Translator:
    """Traduce mensajes del SDK a eventos de dominio. Una instancia por turno."""

    def __init__(self) -> None:
        self._pending: dict[str, FrontName] = {}

    def translate(self, message: Any) -> list[DomainEvent]:
        if isinstance(message, ResultMessage):
            return [
                RunFinished(
                    subtype=message.subtype,
                    stop_reason=message.stop_reason,
                    terminal_reason=message.terminal_reason,
                )
            ]
        if getattr(message, "parent_tool_use_id", None) is not None:
            return []  # actividad interna de un subagente
        if isinstance(message, AssistantMessage):
            return self._from_assistant(message)
        if isinstance(message, UserMessage) and isinstance(message.content, list):
            return self._from_tool_results(message)
        return []

    def _from_assistant(self, message: AssistantMessage) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for block in message.content:
            if isinstance(block, TextBlock):
                events.append(CoordinatorText(block.text))
            elif isinstance(block, ToolUseBlock) and block.name in _DELEGATION_TOOLS:
                try:
                    frente = FrontName(block.input.get("subagent_type"))
                except ValueError:
                    continue
                self._pending[block.id] = frente
                events.append(SubagentStarted(frente, block.id, block.input.get("prompt", "")))
        return events

    def _from_tool_results(self, message: UserMessage) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for block in message.content:
            if not isinstance(block, ToolResultBlock) or block.tool_use_id not in self._pending:
                continue
            frente = self._pending.pop(block.tool_use_id)
            texts = _result_texts(block.content)
            if block.is_error:
                result = FrontResult(frente, {"error": texts[-1]}, {}, FrontStatus.NO_COMPLETADO)
            else:
                # Un bloque válido gana aunque el resultado traiga bloques extra (agentId, uso).
                parsed = [parse_front_result(frente, text) for text in texts]
                result = next((r for r in parsed if r.estado is FrontStatus.COMPLETO), parsed[-1])
            events.append(SubagentFinished(frente, result))
        return events


_INDEPENDENT_FRONTS = (FrontName.REGISTRO_MERCANTIL, FrontName.NOTICIAS, FrontName.RIESGO_CATEGORIA)


def dependency_violations(events: list[DomainEvent]) -> list[str]:
    """Hallazgos si `listas_restrictivas` empezó sin un `registro_mercantil` completo terminado."""
    registry: str | None = None  # None: no terminó · "completo" · "incompleto"
    violations: list[str] = []
    for event in events:
        if isinstance(event, SubagentFinished) and event.frente is FrontName.REGISTRO_MERCANTIL:
            complete = event.result is not None and event.result.estado is FrontStatus.COMPLETO
            registry = "completo" if complete else "incompleto"
        elif (
            isinstance(event, SubagentStarted)
            and event.frente is FrontName.LISTAS_RESTRICTIVAS
            and registry != "completo"
        ):
            reason = (
                "antes de que registro_mercantil terminara"
                if registry is None
                else "sin que registro_mercantil terminara con resultado completo"
            )
            violations.append(
                f"listas_restrictivas se inició {reason} (tool_use_id={event.tool_use_id})"
            )
    return violations


def parallelism_violations(events: list[DomainEvent]) -> list[str]:
    """Hallazgos si un frente independiente se lanzó por primera vez cuando otro ya había terminado.

    Un reintento (el frente ya se había lanzado antes) no cuenta como violación.
    """
    started: set[FrontName] = set()
    any_finished: str | None = None
    violations: list[str] = []
    for event in events:
        if isinstance(event, SubagentFinished) and event.frente in _INDEPENDENT_FRONTS:
            any_finished = any_finished or event.frente.value
        elif isinstance(event, SubagentStarted) and event.frente in _INDEPENDENT_FRONTS:
            if event.frente not in started and any_finished is not None:
                violations.append(
                    f"{event.frente.value} se inició después de que {any_finished} terminara: "
                    "los frentes independientes deben lanzarse juntos"
                )
            started.add(event.frente)
    return violations
