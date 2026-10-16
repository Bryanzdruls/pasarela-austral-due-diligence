"""Sesión multi-turno del coordinador: un cliente del SDK por conversación."""

import contextlib
from collections.abc import AsyncIterator
from typing import Any

from claude_agent_sdk import ClaudeSDKClient, ResultError, ResultMessage

from due_diligence.events import DomainEvent, RunFinished, Translator
from due_diligence.options import build_options
from due_diligence.rules import CaseBook


class DueDiligenceSession:
    """Una conversación con el analista. El cliente conserva el contexto entre turnos.

    Cada turno termina solo cuando el SDK entrega el ResultMessage (razón de parada del
    modelo); no hay contador de iteraciones ni lectura del texto para decidirlo. Todo turno
    cierra con un `RunFinished`: si el SDK no entregó resultado, es un `RunFinished` de error.
    """

    def __init__(self, options: Any = None, client_factory: Any = ClaudeSDKClient):
        # Un CaseBook por conversación: lo identificado, consultado y declarado no se comparte.
        self.book = CaseBook()
        self._options = options if options is not None else build_options(self.book)
        self._client_factory = client_factory
        self._client: Any = None
        self._turn_open = False

    async def __aenter__(self) -> "DueDiligenceSession":
        self._client = self._client_factory(self._options)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        client, self._client = self._client, None
        if client is not None:
            await client.__aexit__(*exc)

    async def _abandon_open_turn(self) -> None:
        """Interrumpe y drena un turno dejado a medias para no contaminar el siguiente."""
        await self._client.interrupt()
        with contextlib.suppress(ResultError):
            async for message in self._client.receive_response():
                if isinstance(message, ResultMessage):
                    break
        self._turn_open = False

    async def ask(self, text: str) -> AsyncIterator[DomainEvent]:
        if self._client is None:
            raise RuntimeError("La sesión no está abierta: usa `async with DueDiligenceSession()`.")
        if self._turn_open:
            await self._abandon_open_turn()

        translator = Translator()
        finished = False
        try:
            await self._client.query(text)
            # Solo tras enviar la consulta existe un turno que abandonar: si `query` falla, el
            # turno nunca empezó y no se marca abierto (el siguiente no intentaría drenarlo).
            self._turn_open = True
            async for message in self._client.receive_response():
                for event in translator.translate(message):
                    if isinstance(event, RunFinished):
                        finished = True
                        self._turn_open = False
                    yield event
        except ResultError:
            # El SDK lanza ResultError tras un ResultMessage de error (p. ej. error_max_turns): el
            # turno ya terminó y su resultado se entregó en RunFinished. Antes, no se oculta.
            if not finished:
                async for event in self._close_with_error("ResultError"):
                    yield event
                raise
        except Exception as exc:
            if not finished:
                async for event in self._close_with_error(type(exc).__name__):
                    yield event
            raise
        if not finished:
            self._turn_open = False
            yield RunFinished("error_stream_ended", None, "stream_ended")

    async def _close_with_error(self, reason: str) -> AsyncIterator[DomainEvent]:
        self._turn_open = False
        yield RunFinished("error_exception", None, reason)
