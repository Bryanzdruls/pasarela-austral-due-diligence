"""Aplicación web del chat (Starlette): rutas del contrato de `specs/007-chat-eventos-visibles`.

Local y sin autenticación: es una demostración que escucha solo en 127.0.0.1. Todo lo que muestra
(texto del modelo y de las fuentes) viaja como datos JSON y la página lo inserta como texto.
"""

import asyncio
import json
import re
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeSDKClient
from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Route

from due_diligence.web.conversacion import Conversacion, TextoInvalido, TurnoEnCurso

PAGINA = Path(__file__).parent / "static" / "index.html"
_ID = re.compile(r"^[0-9a-f]{32}$")
_TERMINALES = ("fin", "error")


def _json(codigo: int, **datos: Any) -> JSONResponse:
    return JSONResponse(datos, status_code=codigo)


def crear_app(client_factory: Any = ClaudeSDKClient) -> Starlette:
    conversaciones: dict[str, Conversacion] = {}

    def buscar(request: Request) -> Conversacion:
        cid = request.path_params["cid"]
        conversacion = conversaciones.get(cid) if _ID.fullmatch(cid) else None
        if conversacion is None:
            raise HTTPException(404, "Conversación inexistente")
        return conversacion

    async def pagina(request: Request) -> Response:
        return FileResponse(PAGINA, media_type="text/html")

    async def estado(request: Request) -> Response:
        return _json(200, estado="ok", conversaciones=len(conversaciones))

    async def crear_conversacion(request: Request) -> Response:
        cid = uuid.uuid4().hex
        conversaciones[cid] = Conversacion(client_factory)
        return _json(201, id=cid)

    async def enviar(request: Request) -> Response:
        conversacion = buscar(request)
        try:
            cuerpo = await request.json()
        except ValueError:
            return _json(422, error="El cuerpo debe ser JSON con el campo 'texto'.")
        texto = cuerpo.get("texto") if isinstance(cuerpo, dict) else None
        try:
            await conversacion.enviar(texto)
        except TextoInvalido as exc:
            return _json(422, error=str(exc))
        except TurnoEnCurso as exc:
            return _json(409, error=str(exc))
        return _json(202, estado="en_curso")

    async def eventos(request: Request) -> Response:
        conversacion = buscar(request)
        hasta_fin = request.query_params.get("hasta_fin") == "1"
        pasado, cola = conversacion.suscribir()

        async def flujo() -> AsyncIterator[dict[str, str]]:
            try:
                for evento in pasado:
                    yield {"data": json.dumps(evento, ensure_ascii=False)}
                # Con el historial ya terminado en un fin/error no hay turno en marcha que esperar.
                if hasta_fin and pasado and pasado[-1]["tipo"] in _TERMINALES:
                    return
                while True:
                    evento = await cola.get()
                    yield {"data": json.dumps(evento, ensure_ascii=False)}
                    if hasta_fin and evento["tipo"] in _TERMINALES:
                        return
            except asyncio.CancelledError:
                raise
            finally:
                conversacion.desuscribir(cola)

        return EventSourceResponse(flujo())

    async def error_interno(request: Request, exc: Exception) -> Response:
        return _json(500, error="Error interno.")

    @asynccontextmanager
    async def vida(app: Starlette) -> AsyncIterator[None]:
        yield
        for conversacion in conversaciones.values():
            await conversacion.cerrar()

    return Starlette(
        routes=[
            Route("/", pagina),
            Route("/api/estado", estado),
            Route("/api/conversaciones", crear_conversacion, methods=["POST"]),
            Route("/api/conversaciones/{cid}/mensajes", enviar, methods=["POST"]),
            Route("/api/conversaciones/{cid}/eventos", eventos),
        ],
        exception_handlers={Exception: error_interno},
        lifespan=vida,
    )
