"""Sesión multi-turno del coordinador: un cliente del SDK por conversación."""

from collections.abc import AsyncIterator
from typing import Any

from claude_agent_sdk import ClaudeSDKClient

from due_diligence.events import DomainEvent, RunFinished, Translator
from due_diligence.options import build_options


class DueDiligenceSession:
    """Una conversación con el analista. El cliente conserva el contexto entre turnos.

    Cada turno termina solo cuando el SDK entrega el ResultMessage (razón de parada del
    modelo); no hay contador de iteraciones ni lectura del texto para decidirlo.
    """

    def __init__(self, options: Any = None, client_factory: Any = ClaudeSDKClient):
        self._options = options if options is not None else build_options()
        self._client_factory = client_factory
        self._client: Any = None

    async def __aenter__(self) -> "DueDiligenceSession":
        self._client = self._client_factory(self._options)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        client, self._client = self._client, None
        if client is not None:
            await client.__aexit__(*exc)

    async def ask(self, text: str) -> AsyncIterator[DomainEvent]:
        if self._client is None:
            raise RuntimeError("La sesión no está abierta: usa `async with DueDiligenceSession()`.")
        translator = Translator()
        finished = False
        await self._client.query(text)
        try:
            async for message in self._client.receive_response():
                for event in translator.translate(message):
                    finished = finished or isinstance(event, RunFinished)
                    yield event
        except Exception:
            # El SDK puede lanzar tras un ResultMessage de error (p. ej. error_max_turns): el
            # turno ya terminó y su resultado se entregó en RunFinished. Antes de eso, no se oculta.
            if not finished:
                raise
