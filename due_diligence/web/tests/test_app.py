"""La aplicación web con el cliente falso: rutas del contrato, validación y flujo SSE."""

import asyncio
import json
import threading

import pytest
from starlette.testclient import TestClient

from due_diligence.tests.fakes import (
    FakeClient,
    FakeClientFactory,
    agent_call,
    assistant,
    result,
    text,
    tool_result,
)
from due_diligence.web.app import crear_app

REGISTRO = json.dumps(
    {
        "contenido": {"razon_social": "Comercio de prueba SAS"},
        "metadatos": {"fuente": "registro_ficticio", "fecha": "2026-01-01"},
    }
)


def un_turno(respuesta="Listo"):
    return [
        assistant(agent_call("tu_1", "registro_mercantil", "Busca CO-XX-0001")),
        tool_result("tu_1", REGISTRO),
        assistant(text(respuesta)),
        result(),
    ]


@pytest.fixture
def cliente():
    with TestClient(crear_app(FakeClientFactory([un_turno(), un_turno("segundo")]))) as c:
        yield c


def crear(cliente):
    respuesta = cliente.post("/api/conversaciones")
    assert respuesta.status_code == 201
    return respuesta.json()["id"]


def eventos(cliente, cid):
    """Lee el flujo SSE hasta el fin del turno y devuelve los eventos decodificados."""
    with cliente.stream("GET", f"/api/conversaciones/{cid}/eventos?hasta_fin=1") as flujo:
        assert flujo.headers["content-type"].startswith("text/event-stream")
        lineas = [linea for linea in flujo.iter_lines() if linea.startswith("data:")]
    return [json.loads(linea[len("data:") :].strip()) for linea in lineas]


def test_the_status_route_answers_without_the_model(cliente):
    assert cliente.get("/api/estado").json() == {"estado": "ok", "conversaciones": 0}
    crear(cliente)
    assert cliente.get("/api/estado").json()["conversaciones"] == 1


def test_a_message_starts_the_turn_and_the_stream_delivers_it_in_the_contract_format(cliente):
    cid = crear(cliente)
    respuesta = cliente.post(
        f"/api/conversaciones/{cid}/mensajes", json={"texto": "Caso CO-XX-0001"}
    )
    assert respuesta.status_code == 202
    vistos = eventos(cliente, cid)
    assert [e["tipo"] for e in vistos] == [
        "analista",
        "delegacion",
        "resultado",
        "coordinador",
        "fin",
    ]
    for evento in vistos:
        assert set(evento) == {"n", "tipo", "titulo", "detalle", "hora", "extra"}
    assert vistos[0]["detalle"] == "Caso CO-XX-0001" and vistos[3]["detalle"] == "Listo"


def test_a_reload_gets_the_same_history(cliente):
    cid = crear(cliente)
    cliente.post(f"/api/conversaciones/{cid}/mensajes", json={"texto": "hola"})
    primero = eventos(cliente, cid)
    assert eventos(cliente, cid) == primero


def test_a_second_turn_extends_the_same_conversation(cliente):
    cid = crear(cliente)
    cliente.post(f"/api/conversaciones/{cid}/mensajes", json={"texto": "uno"})
    eventos(cliente, cid)
    cliente.post(f"/api/conversaciones/{cid}/mensajes", json={"texto": "dos"})
    vistos = eventos(cliente, cid)
    assert [e["n"] for e in vistos] == list(range(1, len(vistos) + 1))
    assert [e["detalle"] for e in vistos if e["tipo"] == "analista"] == ["uno", "dos"]
    assert vistos[-1]["tipo"] == "fin" and vistos[-2]["detalle"] == "segundo"


@pytest.mark.parametrize("cuerpo", [{"texto": ""}, {"texto": "   "}, {"texto": "x" * 4001}, {}, []])
def test_an_empty_long_or_malformed_message_is_422_and_nothing_is_published(cliente, cuerpo):
    cid = crear(cliente)
    assert cliente.post(f"/api/conversaciones/{cid}/mensajes", json=cuerpo).status_code == 422
    assert (
        cliente.post(f"/api/conversaciones/{cid}/mensajes", content=b"no json").status_code == 422
    )


def test_a_message_while_a_turn_runs_is_409():
    puerta = threading.Event()

    class Bloqueado(FakeClient):
        """Cliente cuyo turno no termina hasta que se le deja."""

        async def receive_response(self):
            while not puerta.is_set():
                await asyncio.sleep(0.01)
            async for m in super().receive_response():
                yield m

    with TestClient(crear_app(lambda options=None: Bloqueado([un_turno()]))) as c:
        cid = crear(c)
        assert (
            c.post(f"/api/conversaciones/{cid}/mensajes", json={"texto": "uno"}).status_code == 202
        )
        segundo = c.post(f"/api/conversaciones/{cid}/mensajes", json={"texto": "dos"})
        assert segundo.status_code == 409
        puerta.set()
        assert eventos(c, cid)[-1]["tipo"] == "fin"


@pytest.mark.parametrize("cid", ["0" * 32, "no-es-un-id", "../etc"])
def test_an_unknown_or_malformed_conversation_id_is_404(cliente, cid):
    assert (
        cliente.post(f"/api/conversaciones/{cid}/mensajes", json={"texto": "x"}).status_code == 404
    )
    assert cliente.get(f"/api/conversaciones/{cid}/eventos?hasta_fin=1").status_code == 404


def test_unknown_routes_are_404(cliente):
    assert cliente.get("/nada").status_code == 404


def test_an_internal_error_does_not_expose_its_body(monkeypatch):
    from due_diligence.web.conversacion import Conversacion

    async def explota(self, texto):
        raise RuntimeError("secreto interno C:/privado")

    monkeypatch.setattr(Conversacion, "enviar", explota)
    with TestClient(crear_app(FakeClientFactory([])), raise_server_exceptions=False) as c:
        cid = crear(c)
        respuesta = c.post(f"/api/conversaciones/{cid}/mensajes", json={"texto": "x"})
    assert respuesta.status_code == 500
    assert "secreto" not in respuesta.text and "privado" not in respuesta.text


def test_the_page_is_served_as_html(cliente):
    respuesta = cliente.get("/")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/html")
    assert "<html" in respuesta.text.lower()


def test_a_lone_surrogate_is_rejected_and_the_stream_still_works(cliente):
    cid = crear(cliente)
    cuerpo = b'{"texto": "ab\ud800cd"}'  # JSON válido con un sustituto suelto
    respuesta = cliente.post(
        f"/api/conversaciones/{cid}/mensajes",
        content=cuerpo,
        headers={"Content-Type": "application/json"},
    )
    assert respuesta.status_code == 422
    cliente.post(f"/api/conversaciones/{cid}/mensajes", json={"texto": "hola"})
    assert eventos(cliente, cid)[-1]["tipo"] == "fin"
