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
