"""La conversación del chat, con el cliente falso: turnos en orden, uno a la vez, con historial."""

import asyncio
import json

import pytest

from due_diligence.tests.fakes import (
    FakeClient,
    FakeClientFactory,
    agent_call,
    assistant,
    result,
    text,
    tool_result,
)
from due_diligence.web.conversacion import Conversacion, TextoInvalido, TurnoEnCurso

PREFIX = "mcp__pasarela-fuentes__"
REGISTRO = json.dumps(
    {
        "contenido": {"razon_social": "Comercio de prueba SAS"},
        "metadatos": {"fuente": "registro_ficticio", "fecha": "2026-01-01"},
    }
)


def un_turno(texto="Listo"):
    return [
        assistant(agent_call("tu_1", "registro_mercantil", "Busca CO-XX-0001")),
        tool_result("tu_1", REGISTRO),
        assistant(text(texto)),
        result(),
    ]


async def turno(conv, mensaje="hola"):
    await conv.enviar(mensaje)
    await conv.esperar_turno()


def tipos(conv):
    return [e["tipo"] for e in conv.historial]


async def test_a_turn_publishes_the_analyst_the_delegation_the_result_the_text_and_the_end():
    conv = Conversacion(FakeClientFactory([un_turno("Listo")]))
    await turno(conv, "Due diligence de CO-XX-0001")
    await conv.cerrar()
    assert tipos(conv) == ["analista", "delegacion", "resultado", "coordinador", "fin"]
    assert [e["n"] for e in conv.historial] == [1, 2, 3, 4, 5]
    assert conv.historial[0]["detalle"] == "Due diligence de CO-XX-0001"
    assert conv.historial[3]["detalle"] == "Listo"


async def test_two_turns_reuse_the_same_session_and_keep_numbering():
    factory = FakeClientFactory([un_turno("uno"), [assistant(text("dos")), result()]])
    conv = Conversacion(factory)
    await turno(conv, "primero")
    await turno(conv, "segundo")
    await conv.cerrar()
    assert len(factory.created) == 1
    assert factory.created[0].queries == ["primero", "segundo"]
    assert [e["n"] for e in conv.historial] == list(range(1, len(conv.historial) + 1))
    assert tipos(conv).count("analista") == 2 and tipos(conv).count("fin") == 2
    assert factory.created[0].closed


async def test_a_message_while_a_turn_is_running_is_rejected_and_not_published():
    gate = asyncio.Event()

    class Lento(FakeClient):
        async def receive_response(self):
            await gate.wait()
            async for m in super().receive_response():
                yield m

    conv = Conversacion(lambda options=None: Lento([un_turno()]))
    await conv.enviar("uno")
    assert conv.en_curso
    with pytest.raises(TurnoEnCurso):
        await conv.enviar("dos")
    assert tipos(conv) == ["analista"]
    gate.set()
    await conv.esperar_turno()
    assert not conv.en_curso
    await conv.cerrar()


@pytest.mark.parametrize("mensaje", ["", "   ", "x" * 4001, None, 5, "ab\ud800cd"])
async def test_an_empty_too_long_non_text_or_unencodable_message_is_rejected(mensaje):
    conv = Conversacion(FakeClientFactory([un_turno()]))
    with pytest.raises(TextoInvalido):
        await conv.enviar(mensaje)
    assert conv.historial == [] and not conv.en_curso


async def test_a_late_subscriber_gets_the_history_and_then_the_live_events_and_two_see_the_same():
    gate = asyncio.Event()

    class Lento(FakeClient):
        async def receive_response(self):
            await gate.wait()
            async for m in super().receive_response():
                yield m

    conv = Conversacion(lambda options=None: Lento([un_turno()]))
    await conv.enviar("uno")
    pasado, cola_a = conv.suscribir()
    _, cola_b = conv.suscribir()
    assert [e["tipo"] for e in pasado] == ["analista"]
    gate.set()
    await conv.esperar_turno()
    vivos_a = [cola_a.get_nowait() for _ in range(cola_a.qsize())]
    vivos_b = [cola_b.get_nowait() for _ in range(cola_b.qsize())]
    assert [e["tipo"] for e in vivos_a] == ["delegacion", "resultado", "coordinador", "fin"]
    assert vivos_a == vivos_b
    conv.desuscribir(cola_a)
    await conv.cerrar()


async def test_a_session_error_publishes_one_readable_error_and_the_conversation_still_works():
    class Roto(FakeClient):
        async def query(self, prompt, session_id="default"):
            if not self.queries:
                self.queries.append(prompt)
                raise RuntimeError("secreto interno /ruta/privada")
            await super().query(prompt, session_id)

    conv = Conversacion(lambda options=None: Roto([[assistant(text("bien")), result()]]))
    await turno(conv, "primero")
    assert tipos(conv).count("error") == 1
    error = next(e for e in conv.historial if e["tipo"] == "error")
    assert "RuntimeError" in error["detalle"] and "/ruta/privada" not in error["detalle"]
    await turno(conv, "segundo")
    assert "coordinador" in tipos(conv) and tipos(conv)[-1] == "fin"
    await conv.cerrar()


async def test_blocks_report_and_escalation_appear_in_order_between_the_turn_events():
    async def acciones(options):
        pre = options.hooks["PreToolUse"][0].hooks
        for hook in pre:  # informe sin haber identificado al comercio: la regla lo bloquea
            await hook(
                {
                    "tool_name": PREFIX + "registrar_informe",
                    "tool_input": {"comercio_id": "CO-XX-0001", "recomendacion": "habilitar"},
                },
                None,
                None,
            )
        post = options.hooks["PostToolUse"][0].hooks
        for hook in post:
            await hook(
                {
                    "tool_name": PREFIX + "registrar_informe",
                    "tool_input": {"comercio_id": "CO-XX-0001", "recomendacion": "no_habilitar"},
                    "tool_response": json.dumps({"ok": True, "content": {"informe_id": "INF-1"}}),
                },
                None,
                None,
            )

    class ConHooks(FakeClient):
        def __init__(self, options, turns):
            super().__init__(turns)
            self.options = options

        async def receive_response(self):
            await acciones(self.options)
            async for m in super().receive_response():
                yield m

    conv = Conversacion(lambda options=None: ConHooks(options, [un_turno()]))
    await turno(conv, "caso")
    await conv.cerrar()
    assert tipos(conv) == [
        "analista",
        "bloqueo",
        "informe",
        "delegacion",
        "resultado",
        "coordinador",
        "fin",
    ]
    bloqueo = conv.historial[1]
    assert bloqueo["extra"]["agente"] == "coordinador" and bloqueo["extra"]["regla"]
    assert "INF-1" in conv.historial[2]["titulo"]


async def test_closing_a_conversation_that_never_ran_is_safe():
    conv = Conversacion(FakeClientFactory([]))
    await conv.cerrar()
