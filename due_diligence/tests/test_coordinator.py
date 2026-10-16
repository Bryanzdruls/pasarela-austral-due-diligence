import pytest

from due_diligence.coordinator import DueDiligenceSession
from due_diligence.events import CoordinatorText, RunFinished
from due_diligence.tests.fakes import FakeClientFactory, assistant, result, text


async def _collect(session, message):
    return [event async for event in session.ask(message)]


async def test_a_turn_emits_text_and_ends_with_a_single_run_finished():
    factory = FakeClientFactory([[assistant(text("Informe listo.")), result()]])
    async with DueDiligenceSession(client_factory=factory) as session:
        events = await _collect(session, "Necesito el due diligence de CO-TV-0001")
    assert [type(e) for e in events] == [CoordinatorText, RunFinished]
    assert events[0].text == "Informe listo."
    finished = events[-1]
    assert (finished.subtype, finished.stop_reason, finished.terminal_reason) == (
        "success",
        "end_turn",
        "completed",
    )


async def test_two_turns_reuse_the_same_client():  # FR-013
    factory = FakeClientFactory(
        [
            [assistant(text("Primer informe.")), result()],
            [assistant(text("Seguimiento respondido.")), result()],
        ]
    )
    async with DueDiligenceSession(client_factory=factory) as session:
        first = await _collect(session, "Due diligence de CO-TV-0001")
        second = await _collect(session, "¿Y las noticias?")
    assert len(factory.created) == 1
    assert factory.created[0].queries == ["Due diligence de CO-TV-0001", "¿Y las noticias?"]
    assert isinstance(first[-1], RunFinished) and isinstance(second[-1], RunFinished)
    assert [e.text for e in second if isinstance(e, CoordinatorText)] == ["Seguimiento respondido."]


async def test_client_is_opened_on_enter_and_closed_on_exit():
    factory = FakeClientFactory([[assistant(text("ok")), result()]])
    session = DueDiligenceSession(client_factory=factory)
    assert factory.created == []
    async with session:
        client = factory.created[0]
        assert client.opened and not client.closed
    assert client.closed


async def test_default_options_are_the_coordinator_options():
    factory = FakeClientFactory([])
    async with DueDiligenceSession(client_factory=factory):
        pass
    assert factory.options_received[0].tools == ["Agent"]


async def test_explicit_options_are_passed_through():
    factory = FakeClientFactory([])
    sentinel = object()
    async with DueDiligenceSession(options=sentinel, client_factory=factory):
        pass
    assert factory.options_received[0] is sentinel


async def test_ask_outside_a_session_is_an_error():
    session = DueDiligenceSession(client_factory=FakeClientFactory([]))
    with pytest.raises(RuntimeError):
        await _collect(session, "hola")


# --- US3: orden de eventos de un turno completo y seguimiento (FR-013, SC-004) ---------

import json  # noqa: E402
import re  # noqa: E402
from pathlib import Path  # noqa: E402

from due_diligence.events import (  # noqa: E402
    SubagentFinished,
    SubagentStarted,
    dependency_violations,
    parallelism_violations,
)
from due_diligence.tests.fakes import agent_call, tool_result  # noqa: E402


def _ok(frente, fuente):
    return json.dumps(
        {
            "contenido": {"frente": frente},
            "metadatos": {"fuente": fuente, "fecha": "2026-10-16T10:00:00+00:00"},
        }
    )


def _full_investigation_turn():
    return [
        assistant(
            agent_call("t1", "registro_mercantil", "Identifica CO-TV-0001"),
            agent_call("t2", "noticias", "Noticias de Tienda Verde SAS"),
            agent_call("t3", "riesgo_categoria", "Riesgo de suplementos dietarios"),
        ),
        tool_result("t1", _ok("registro_mercantil", "registro_mercantil_ficticio")),
        tool_result("t2", _ok("noticias", "noticias_ficticias")),
        tool_result("t3", _ok("riesgo_categoria", "catalogo_riesgo_ficticio")),
        assistant(agent_call("t4", "listas_restrictivas", "Verifica CO-TV-0001 y PE-0001")),
        tool_result("t4", _ok("listas_restrictivas", "listas_restrictivas_ficticias")),
        assistant(text("Informe: derivar a un oficial de cumplimiento.")),
        result(),
    ]


async def test_a_full_turn_emits_events_in_the_contract_order():
    factory = FakeClientFactory([_full_investigation_turn()])
    async with DueDiligenceSession(client_factory=factory) as session:
        events = await _collect(session, "Due diligence de Tienda Verde SAS CO-TV-0001")
    kinds = [type(e).__name__ for e in events]
    assert kinds == [
        "SubagentStarted",
        "SubagentStarted",
        "SubagentStarted",
        "SubagentFinished",
        "SubagentFinished",
        "SubagentFinished",
        "SubagentStarted",
        "SubagentFinished",
        "CoordinatorText",
        "RunFinished",
    ]
    assert dependency_violations(events) == []
    assert parallelism_violations(events) == []
    listas = [e for e in events if isinstance(e, SubagentStarted)][-1]
    assert listas.frente.value == "listas_restrictivas"


async def test_a_followup_turn_launches_no_subagents():
    factory = FakeClientFactory(
        [_full_investigation_turn(), [assistant(text("Las noticias: ...")), result()]]
    )
    async with DueDiligenceSession(client_factory=factory) as session:
        await _collect(session, "Due diligence de CO-TV-0001")
        second = await _collect(session, "¿Y qué dijeron las noticias?")
    assert not [e for e in second if isinstance(e, (SubagentStarted, SubagentFinished))]
    assert [type(e).__name__ for e in second] == ["CoordinatorText", "RunFinished"]


# --- US4: el turno termina por el ResultMessage, no por texto ni por contador (SC-005) --


async def test_a_closing_word_in_the_text_does_not_end_the_turn():
    turn = [
        assistant(text("Listo, terminado."), agent_call("t1", "noticias", "Noticias")),
        tool_result("t1", _ok("noticias", "noticias_ficticias")),
        assistant(text("Informe final.")),
        result(),
    ]
    factory = FakeClientFactory([turn])
    async with DueDiligenceSession(client_factory=factory) as session:
        events = await _collect(session, "x")
    texts = [e.text for e in events if isinstance(e, CoordinatorText)]
    assert texts == ["Listo, terminado.", "Informe final."]
    assert any(isinstance(e, SubagentFinished) for e in events)
    assert (
        isinstance(events[-1], RunFinished) and sum(isinstance(e, RunFinished) for e in events) == 1
    )


async def test_turns_of_very_different_length_all_end_at_the_result_message():
    long_turn = [assistant(text(f"paso {i}")) for i in range(200)] + [result()]
    short_turn = [result()]
    factory = FakeClientFactory([long_turn, short_turn])
    async with DueDiligenceSession(client_factory=factory) as session:
        first = await _collect(session, "largo")
        second = await _collect(session, "corto")
    assert len([e for e in first if isinstance(e, CoordinatorText)]) == 200
    assert isinstance(first[-1], RunFinished) and isinstance(second[-1], RunFinished)


async def test_max_turns_error_is_reflected_and_an_exception_after_it_is_contained():
    turn = [
        assistant(text("parcial")),
        result(
            subtype="error_max_turns", stop_reason=None, terminal_reason="max_turns", is_error=True
        ),
    ]
    factory = FakeClientFactory([turn], raise_after=RuntimeError("max turns alcanzado"))
    async with DueDiligenceSession(client_factory=factory) as session:
        events = await _collect(session, "x")  # no debe lanzar
    finished = events[-1]
    assert isinstance(finished, RunFinished)
    assert finished.subtype == "error_max_turns" and finished.stop_reason is None
    assert finished.terminal_reason == "max_turns"


async def test_an_exception_before_any_result_message_is_not_hidden():
    factory = FakeClientFactory(
        [[assistant(text("a medias"))]], raise_after=RuntimeError("se cayó")
    )
    async with DueDiligenceSession(client_factory=factory) as session:
        with pytest.raises(RuntimeError, match="se cayó"):
            await _collect(session, "x")


def test_the_loop_code_never_sets_a_turn_limit():
    root = Path(__file__).resolve().parents[1]
    for name in ("coordinator.py", "options.py"):
        assert not re.search(r"max_turns\s*=", (root / name).read_text(encoding="utf-8")), name
