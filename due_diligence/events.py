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


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


class FrontName(StrEnum):
    REGISTRO_MERCANTIL = "registro_mercantil"
    LISTAS_RESTRICTIVAS = "listas_restrictivas"
    NOTICIAS = "noticias"
    RIESGO_CATEGORIA = "riesgo_categoria"


class FrontStatus(StrEnum):
    COMPLETO = "completo"
    NO_ESTRUCTURADO = "no_estructurado"
    NO_COMPLETADO = "no_completado"


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


DomainEvent = SubagentStarted | SubagentFinished | CoordinatorText | RunFinished


_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)
_DELEGATION_TOOLS = ("Agent", "Task")


def _result_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return ""


def parse_front_result(frente: FrontName, raw: str) -> FrontResult:
    """Convierte la respuesta de un subagente en FrontResult; nunca da por buena una mal formada."""
    fenced = _FENCE.match(raw)
    candidate = (fenced.group(1) if fenced else raw).strip()
    try:
        data = json.loads(candidate)
    except (ValueError, TypeError):
        data = None
    if isinstance(data, dict):
        contenido, metadatos = data.get("contenido"), data.get("metadatos")
        if (
            isinstance(contenido, dict)
            and isinstance(metadatos, dict)
            and all(isinstance(metadatos.get(k), str) and metadatos[k].strip() for k in _META_KEYS)
        ):
            return FrontResult(
                frente, contenido, {k: metadatos[k] for k in _META_KEYS}, FrontStatus.COMPLETO
            )
    return FrontResult(frente, {"texto_sin_estructura": raw}, {}, FrontStatus.NO_ESTRUCTURADO)


_META_KEYS = ("fuente", "fecha")


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
            raw = _result_text(block.content)
            if block.is_error:
                result = FrontResult(frente, {"error": raw}, {}, FrontStatus.NO_COMPLETADO)
            else:
                result = parse_front_result(frente, raw)
            events.append(SubagentFinished(frente, result))
        return events


_INDEPENDENT_FRONTS = (FrontName.REGISTRO_MERCANTIL, FrontName.NOTICIAS, FrontName.RIESGO_CATEGORIA)


def dependency_violations(events: list[DomainEvent]) -> list[str]:
    """Hallazgos si `listas_restrictivas` empezó antes de que `registro_mercantil` terminara."""
    registry_done = False
    violations: list[str] = []
    for event in events:
        if isinstance(event, SubagentFinished) and event.frente is FrontName.REGISTRO_MERCANTIL:
            registry_done = True
        elif (
            isinstance(event, SubagentStarted)
            and event.frente is FrontName.LISTAS_RESTRICTIVAS
            and not registry_done
        ):
            violations.append(
                "listas_restrictivas se inició antes de que registro_mercantil terminara "
                f"(tool_use_id={event.tool_use_id})"
            )
    return violations


def parallelism_violations(events: list[DomainEvent]) -> list[str]:
    """Hallazgos si un frente independiente empezó después de que otro independiente terminó."""
    any_finished: str | None = None
    violations: list[str] = []
    for event in events:
        if isinstance(event, SubagentFinished) and event.frente in _INDEPENDENT_FRONTS:
            any_finished = any_finished or event.frente.value
        elif (
            isinstance(event, SubagentStarted)
            and event.frente in _INDEPENDENT_FRONTS
            and any_finished is not None
        ):
            violations.append(
                f"{event.frente.value} se inició después de que {any_finished} terminara: "
                "los frentes independientes deben lanzarse juntos"
            )
    return violations
