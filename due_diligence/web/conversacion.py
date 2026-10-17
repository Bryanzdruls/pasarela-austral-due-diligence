"""Una conversación del chat: turnos de uno en uno, historial reproducible y suscriptores.

Reutiliza una sola `DueDiligenceSession` (un cliente del SDK) entre turnos, como la consola, así que
el coordinador conserva el contexto. Quien se conecta o recarga recibe primero el historial y luego
los eventos en vivo. Todo lo que se publica pasa por `a_vista`, la única que decide cómo se lee.
"""

import asyncio
import contextlib
import re
from datetime import UTC, datetime
from typing import Any

from claude_agent_sdk import ClaudeSDKClient

from due_diligence.coordinator import DueDiligenceSession
from due_diligence.events import DomainEvent, RunFinished
from due_diligence.options import build_options
from due_diligence.rules import CaseBook
from due_diligence.web.observadores import observador_bloqueo, observador_post
from due_diligence.web.vista import a_vista, vista_analista, vista_error

MAX_TEXTO = 4000


class TurnoEnCurso(Exception):
    """Ya hay un turno en marcha: el SDK es secuencial, un turno a la vez."""


class TextoInvalido(ValueError):
    """El mensaje del analista está vacío, es demasiado largo o no es texto."""


def _ahora() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


_SUSTITUTO_SUELTO = re.compile("[\ud800-\udfff]")


def _sin_sustitutos(valor: Any) -> Any:
    """Cambia los sustitutos UTF-16 sueltos (inválidos en UTF-8) por U+FFFD, en toda la tarjeta.

    El texto del analista se rechaza al entrar, pero el del modelo y el de las fuentes no: un
    sustituto suelto rompería el flujo SSE en cada reconexión y el historial no se recuperaría.
    """
    if isinstance(valor, str):
        return _SUSTITUTO_SUELTO.sub("�", valor)
    if isinstance(valor, list):
        return [_sin_sustitutos(item) for item in valor]
    if isinstance(valor, dict):
        return {clave: _sin_sustitutos(item) for clave, item in valor.items()}
    return valor


class Conversacion:
    def __init__(self, client_factory: Any = ClaudeSDKClient):
        self.historial: list[dict[str, Any]] = []
        self._suscriptores: list[asyncio.Queue] = []
        self._tarea: asyncio.Task | None = None
        self._abierta = False
        # Un CaseBook por conversación, compartido por todos los hooks (como en la consola).
        book = CaseBook()
        options = build_options(
            book,
            on_decision=observador_bloqueo(self._publicar_evento),
            extra_post=observador_post(self._publicar_evento),
        )
        self._sesion = DueDiligenceSession(options=options, client_factory=client_factory)

    @property
    def en_curso(self) -> bool:
        return self._tarea is not None and not self._tarea.done()

    def suscribir(self) -> tuple[list[dict[str, Any]], asyncio.Queue]:
        """El historial hasta ahora y una cola con lo que llegue después (sin huecos)."""
        cola: asyncio.Queue = asyncio.Queue()
        self._suscriptores.append(cola)
        return list(self.historial), cola

    def desuscribir(self, cola: asyncio.Queue) -> None:
        with contextlib.suppress(ValueError):
            self._suscriptores.remove(cola)

    def _publicar(self, hacer_vista: Any) -> dict[str, Any]:
        vista = _sin_sustitutos(hacer_vista(len(self.historial) + 1))
        self.historial.append(vista)
        for cola in self._suscriptores:
            cola.put_nowait(vista)
        return vista

    def _publicar_evento(self, evento: DomainEvent) -> None:
        self._publicar(lambda n: a_vista(evento, n))

    async def enviar(self, texto: Any) -> None:
        """Acepta el mensaje y arranca el turno; el resultado llega por los eventos."""
        if not isinstance(texto, str) or not texto.strip() or len(texto) > MAX_TEXTO:
            raise TextoInvalido(
                f"El mensaje debe ser texto, no vacío y de hasta {MAX_TEXTO} caracteres."
            )
        try:
            texto.encode(
                "utf-8"
            )  # un sustituto suelto rompería el flujo de eventos al reproducirlo
        except UnicodeEncodeError:
            raise TextoInvalido(
                "El mensaje contiene caracteres que no se pueden mostrar."
            ) from None
        if self.en_curso:
            raise TurnoEnCurso("Hay un turno en curso: espera a que termine.")
        self._publicar(lambda n: vista_analista(texto, _ahora(), n))
        self._tarea = asyncio.create_task(self._turno(texto))

    async def esperar_turno(self) -> None:
        if self._tarea is not None:
            await asyncio.shield(self._tarea)

    async def _turno(self, texto: str) -> None:
        terminado = False
        try:
            if not self._abierta:
                await self._sesion.__aenter__()
                self._abierta = True
            async for evento in self._sesion.ask(texto):
                terminado = terminado or isinstance(evento, RunFinished)
                self._publicar_evento(evento)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - el chat informa y sigue; no muestra el detalle
            if not terminado:
                causa = type(exc).__name__
                self._publicar(lambda n: vista_error(causa, _ahora(), n))

    async def cerrar(self) -> None:
        if self._tarea is not None and not self._tarea.done():
            self._tarea.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._tarea
        if self._abierta:
            self._abierta = False
            with contextlib.suppress(Exception):
                await self._sesion.__aexit__(None, None, None)
