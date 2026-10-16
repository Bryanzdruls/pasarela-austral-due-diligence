"""Tipos de dominio del coordinador: frentes, resultados de frente y eventos."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock


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


class Translator:
    """Traduce mensajes del SDK a eventos de dominio. Una instancia por turno."""

    def translate(self, message: Any) -> list[DomainEvent]:
        if isinstance(message, ResultMessage):
            return [
                RunFinished(
                    subtype=message.subtype,
                    stop_reason=message.stop_reason,
                    terminal_reason=message.terminal_reason,
                )
            ]
        if isinstance(message, AssistantMessage) and message.parent_tool_use_id is None:
            return [CoordinatorText(b.text) for b in message.content if isinstance(b, TextBlock)]
        return []
