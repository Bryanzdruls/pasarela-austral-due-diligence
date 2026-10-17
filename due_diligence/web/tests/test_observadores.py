"""Observadores del chat: convierten lo que el sistema decidió y lo que el servidor confirmó."""

import json

from due_diligence.events import CallBlocked, Escalated, ReportRegistered
from due_diligence.rules import Decision
from due_diligence.web.observadores import observador_bloqueo, observador_post

PREFIX = "mcp__pasarela-fuentes__"


def post(tool, tool_input, response, prefix=PREFIX):
    return {"tool_name": prefix + tool, "tool_input": tool_input, "tool_response": response}


def envelope(content, ok=True):
    return json.dumps({"ok": ok, "content": content, "metadata": {"source": "informes_ficticio"}})


async def run(tool, tool_input, response, prefix=PREFIX):
    emitted = []
    out = await observador_post(emitted.append)(post(tool, tool_input, response, prefix), "t", None)
    assert out == {}
    return emitted


async def test_a_confirmed_report_emits_report_registered_with_the_server_id():
    events = await run(
        "registrar_informe",
        {"comercio_id": "CO-XX-0001", "recomendacion": "no_habilitar"},
        envelope({"informe_id": "INF-0007"}),
    )
    assert events == [
        ReportRegistered("INF-0007", "CO-XX-0001", "no_habilitar", events[0].timestamp)
    ]


async def test_a_confirmed_escalation_emits_escalated_with_the_server_id_and_cause():
    events = await run(
        "escalar_a_cumplimiento",
        {"comercio_id": "CO-XX-0003", "causa": "coincidencia en listas"},
        envelope({"escalamiento_id": "ESC-0002"}),
    )
    assert len(events) == 1 and isinstance(events[0], Escalated)
    assert (events[0].escalamiento_id, events[0].comercio_id, events[0].causa) == (
        "ESC-0002",
        "CO-XX-0003",
        "coincidencia en listas",
    )


async def test_the_short_tool_name_also_works():
    events = await run(
        "registrar_informe",
        {"comercio_id": "CO-XX-0001", "recomendacion": "habilitar"},
        envelope({"informe_id": "INF-0001"}),
        prefix="",
    )
    assert len(events) == 1


async def test_an_error_unreadable_or_foreign_response_emits_nothing():
    args = {"comercio_id": "CO-XX-0001", "recomendacion": "habilitar"}
    assert await run("registrar_informe", args, envelope({"informe_id": "INF-1"}, ok=False)) == []
    assert await run("registrar_informe", args, "no es json") == []
    assert await run("registrar_informe", args, envelope({"otra": "cosa"})) == []
    assert await run("registrar_informe", None, envelope({"informe_id": "INF-1"})) == []
    assert await run("buscar_noticias", args, envelope({"informe_id": "INF-1"})) == []


async def test_an_emit_that_fails_does_not_break_the_hook():
    def boom(event):
        raise RuntimeError("la interfaz falló")

    out = await observador_post(boom)(
        post(
            "registrar_informe",
            {"comercio_id": "CO-XX-0001", "recomendacion": "habilitar"},
            envelope({"informe_id": "INF-1"}),
        ),
        "t",
        None,
    )
    assert out == {}


def test_a_denied_decision_becomes_call_blocked_with_agent_tool_rule_and_reason():
    emitted = []
    observador_bloqueo(emitted.append)(
        {
            "tool_name": PREFIX + "consultar_listas_restrictivas",
            "agent_type": "listas_restrictivas",
        },
        Decision(False, "1", "Regla 1: falta el registro"),
    )
    assert len(emitted) == 1 and isinstance(emitted[0], CallBlocked)
    assert emitted[0].agente == "listas_restrictivas"
    assert emitted[0].herramienta == "consultar_listas_restrictivas"
    assert (emitted[0].regla, emitted[0].motivo) == ("1", "Regla 1: falta el registro")


def test_a_block_by_the_coordinator_has_no_agent_type_and_says_so():
    emitted = []
    observador_bloqueo(emitted.append)(
        {"tool_name": PREFIX + "registrar_informe"},
        Decision(False, "escalamiento", "motivo"),
    )
    assert emitted[0].agente == "coordinador"


async def test_a_report_carries_the_fronts_it_declares_uncovered():
    cobertura = {"noticias": {"estado": "sin_cubrir", "motivo": "fuente caída"}}
    events = await run(
        "registrar_informe",
        {"comercio_id": "CO-XX-0001", "recomendacion": "no_habilitar", "cobertura": cobertura},
        envelope({"informe_id": "INF-0002"}),
    )
    assert events[0].sin_cubrir == ("noticias",)
    sin_declarar = await run(
        "registrar_informe",
        {"comercio_id": "CO-XX-0001", "recomendacion": "habilitar", "cobertura": "todo bien"},
        envelope({"informe_id": "INF-0003"}),
    )
    assert sin_declarar[0].sin_cubrir == ()


def test_one_denied_call_that_two_hooks_reject_is_shown_once():
    emitted = []
    observar = observador_bloqueo(emitted.append)
    llamada = {"tool_name": PREFIX + "consultar_listas_restrictivas", "tool_use_id": "tu_7"}
    observar(llamada, Decision(False, "aislamiento", "no es tu herramienta"))
    observar(llamada, Decision(False, "1", "falta el registro"))
    assert [e.regla for e in emitted] == ["aislamiento"]
    observar({**llamada, "tool_use_id": "tu_8"}, Decision(False, "1", "otra llamada"))
    assert len(emitted) == 2
    sin_id = {"tool_name": PREFIX + "registrar_informe"}
    observar(sin_id, Decision(False, "3", "uno"))
    observar(sin_id, Decision(False, "3", "dos"))
    assert len(emitted) == 4
