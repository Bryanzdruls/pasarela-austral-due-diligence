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


async def test_a_stream_that_ends_without_a_result_still_closes_the_turn_with_run_finished():
    factory = FakeClientFactory([[assistant(text("a medias"))]])
    async with DueDiligenceSession(client_factory=factory) as session:
        events = await _collect(session, "x")
    last = events[-1]
    assert isinstance(last, RunFinished) and last.subtype == "error_stream_ended"
    assert last.stop_reason is None and last.terminal_reason == "stream_ended"


async def test_an_exception_before_a_result_gives_a_terminal_event_and_is_not_hidden():
    factory = FakeClientFactory(
        [[assistant(text("a medias"))]], raise_after=RuntimeError("se cayó")
    )
    events = []
    async with DueDiligenceSession(client_factory=factory) as session:
        with pytest.raises(RuntimeError, match="se cayó"):
            async for event in session.ask("x"):
                events.append(event)
    last = events[-1]
    assert isinstance(last, RunFinished) and last.subtype == "error_exception"
    assert last.terminal_reason == "RuntimeError"


async def test_only_the_sdk_result_error_is_contained_after_a_result():
    from claude_agent_sdk import ResultError

    turn = [assistant(text("parcial")), result(subtype="error_max_turns", is_error=True)]
    contained = FakeClientFactory([turn], raise_after=ResultError("max turns"))
    async with DueDiligenceSession(client_factory=contained) as session:
        events = await _collect(session, "x")
    assert events[-1].subtype == "error_max_turns"

    other = FakeClientFactory(
        [[assistant(text("ok")), result()]], raise_after=OSError("transporte")
    )
    async with DueDiligenceSession(client_factory=other) as session:
        with pytest.raises(OSError, match="transporte"):
            await _collect(session, "x")


async def test_an_abandoned_turn_does_not_contaminate_the_next_one():
    first = [assistant(text("uno")), assistant(text("dos")), assistant(text("tres")), result()]
    second = [assistant(text("segundo turno")), result()]
    factory = FakeClientFactory([first, second])
    async with DueDiligenceSession(client_factory=factory) as session:
        stream = session.ask("primero")
        assert (await anext(stream)).text == "uno"
        await stream.aclose()  # el consumidor abandona a medias
        events = await _collect(session, "segundo")
    client = factory.created[0]
    assert client.interrupted == 1
    assert [e.text for e in events if isinstance(e, CoordinatorText)] == ["segundo turno"]
    assert isinstance(events[-1], RunFinished) and events[-1].subtype == "success"


async def test_a_completed_turn_does_not_trigger_an_interrupt():
    factory = FakeClientFactory(
        [[assistant(text("a")), result()], [assistant(text("b")), result()]]
    )
    async with DueDiligenceSession(client_factory=factory) as session:
        await _collect(session, "1")
        await _collect(session, "2")
    assert factory.created[0].interrupted == 0


def test_the_session_code_never_passes_a_turn_limit():
    import ast

    root = Path(__file__).resolve().parents[1]
    for name in ("coordinator.py", "options.py"):
        tree = ast.parse((root / name).read_text(encoding="utf-8"))
        keywords = [
            k.arg for node in ast.walk(tree) if isinstance(node, ast.Call) for k in node.keywords
        ]
        assert "max_turns" not in keywords, name
        assert "maxTurns" not in keywords, name


class _QueryFails:
    """Cliente cuyo transporte está caído: `query` lanza antes de empezar el turno."""

    def __init__(self, options=None):
        self.interrupted = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def query(self, prompt, session_id="default"):
        raise ConnectionError("transporte caído")

    async def interrupt(self):
        self.interrupted += 1

    async def receive_response(self):
        raise AssertionError("no hay turno que leer: query falló")
        yield  # pragma: no cover


async def test_a_failing_query_still_closes_the_turn_and_does_not_leave_it_open():
    async with DueDiligenceSession(client_factory=_QueryFails) as session:
        events = []
        with pytest.raises(ConnectionError, match="transporte caído"):
            async for event in session.ask("x"):
                events.append(event)
        # el turno nunca empezó: cierra con un evento terminal y no queda marcado como abierto
        assert isinstance(events[-1], RunFinished) and events[-1].subtype == "error_exception"
        assert events[-1].terminal_reason == "ConnectionError"
        # el siguiente intento no intenta interrumpir ni drenar un turno que no existe
        with pytest.raises(ConnectionError):
            async for _ in session.ask("otra vez"):
                pass
        assert session._client.interrupted == 0


async def test_each_conversation_gets_its_own_case_book():
    from due_diligence.rules import CaseBook

    factory = FakeClientFactory([])
    async with DueDiligenceSession(client_factory=factory) as one:
        async with DueDiligenceSession(client_factory=factory) as two:
            assert isinstance(one.book, CaseBook) and isinstance(two.book, CaseBook)
            assert one.book is not two.book


async def test_the_session_hooks_are_bound_to_its_own_case_book():
    factory = FakeClientFactory([])
    async with DueDiligenceSession(client_factory=factory) as session:
        hooks = factory.options_received[0].hooks
        await hooks["UserPromptSubmit"][0].hooks[-1](
            {"prompt": "Due diligence de apuestas"}, None, None
        )
        assert "apuestas" in session.book.declared_text
