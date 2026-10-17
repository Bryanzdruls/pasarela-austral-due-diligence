"""Conversación interactiva por consola: `python -m due_diligence`."""

import asyncio
import os
from collections.abc import Callable, Mapping
from typing import Any

from claude_agent_sdk import ClaudeSDKClient

from due_diligence.coordinator import DueDiligenceSession
from due_diligence.events import (
    CallBlocked,
    CoordinatorText,
    DomainEvent,
    Escalated,
    ReportRegistered,
    RunFinished,
    SubagentFinished,
    SubagentStarted,
)

EXIT_WORD = "salir"


def render_event(event: DomainEvent) -> str:
    stamp = f"[{event.timestamp}]"
    if isinstance(event, SubagentStarted):
        return f"{stamp} > Subagente {event.frente.value} iniciado | encargo: {event.encargo}"
    if isinstance(event, SubagentFinished):
        estado = event.result.estado.value if event.result else "sin resultado"
        return f"{stamp} < Subagente {event.frente.value} terminó | estado: {estado}"
    if isinstance(event, CoordinatorText):
        return f"{stamp} Coordinador: {event.text}"
    if isinstance(event, RunFinished):
        return (
            f"{stamp} Fin del turno | subtype={event.subtype} "
            f"stop_reason={event.stop_reason} terminal_reason={event.terminal_reason}"
        )
    if isinstance(event, CallBlocked):
        return (
            f"{stamp} X Llamada bloqueada | agente: {event.agente} | regla: {event.regla} | "
            f"{event.motivo}"
        )
    if isinstance(event, ReportRegistered):
        return (
            f"{stamp} + Informe {event.informe_id} registrado | {event.comercio_id} | "
            f"recomendación: {event.recomendacion}"
        )
    if isinstance(event, Escalated):
        return (
            f"{stamp} ! Escalamiento {event.escalamiento_id} | {event.comercio_id} | "
            f"causa: {event.causa}"
        )
    return f"{stamp} {event!r}"


async def run_cli(
    read: Callable[[str], str],
    write: Callable[[str], Any],
    client_factory: Any = ClaudeSDKClient,
    env: Mapping[str, str] | None = None,
) -> int:
    env = os.environ if env is None else env
    if not env.get("ANTHROPIC_API_KEY"):
        write(
            "Falta la variable de entorno ANTHROPIC_API_KEY. Defínela en tu entorno "
            "(nunca en el repositorio) y vuelve a intentarlo."
        )
        return 1

    write(f"Conversación de due diligence. Escribe tu solicitud; '{EXIT_WORD}' termina.")
    async with DueDiligenceSession(client_factory=client_factory) as session:
        while True:
            try:
                line = read("Analista> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not line:
                continue
            if line.lower() == EXIT_WORD:
                break
            try:
                async for event in session.ask(line):
                    write(render_event(event))
            except Exception as exc:  # fallo del SDK: se informa sin traceback y se cierra
                write(f"Error durante el turno ({type(exc).__name__}): {exc}")
                return 2
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run_cli(input, print)))


if __name__ == "__main__":
    main()
