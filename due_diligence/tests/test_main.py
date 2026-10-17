from due_diligence.__main__ import render_event, run_cli
from due_diligence.events import CoordinatorText, FrontName, RunFinished, SubagentStarted
from due_diligence.tests.fakes import FakeClientFactory, assistant, result, text


def _io(inputs):
    lines = iter(inputs)
    printed: list[str] = []
    return (lambda prompt="": next(lines)), printed.append, printed


async def test_missing_api_key_stops_with_a_clear_message_and_never_calls_the_model():
    factory = FakeClientFactory([])
    read, write, printed = _io([])
    code = await run_cli(read, write, factory, env={})
    assert code == 1
    assert factory.created == []
    assert any("ANTHROPIC_API_KEY" in line for line in printed)


async def test_interactive_session_ends_with_salir_and_prints_the_events():
    factory = FakeClientFactory([[assistant(text("Informe listo.")), result()]])
    read, write, printed = _io(["Due diligence de CO-TV-0001", "salir"])
    code = await run_cli(read, write, factory, env={"ANTHROPIC_API_KEY": "x"})
    assert code == 0
    assert factory.created[0].queries == ["Due diligence de CO-TV-0001"]
    assert any("Informe listo." in line for line in printed)
    assert factory.created[0].closed


async def test_blank_lines_are_ignored():
    factory = FakeClientFactory([[assistant(text("ok")), result()]])
    read, write, _ = _io(["", "   ", "hola", "salir"])
    await run_cli(read, write, factory, env={"ANTHROPIC_API_KEY": "x"})
    assert factory.created[0].queries == ["hola"]


def test_events_are_rendered_readably_with_encargo_and_timestamp():
    started = SubagentStarted(FrontName.NOTICIAS, "t1", "Busca noticias de Tienda Verde SAS")
    line = render_event(started)
    assert "noticias" in line and "Busca noticias de Tienda Verde SAS" in line
    assert started.timestamp in line
    assert "ok" in render_event(CoordinatorText("ok"))
    assert "success" in render_event(RunFinished("success", "end_turn", "completed"))


async def test_an_sdk_failure_is_reported_without_a_traceback_and_the_exit_code_says_so():
    factory = FakeClientFactory(
        [[assistant(text("a medias"))]], raise_after=RuntimeError("se cayó")
    )
    read, write, printed = _io(["hola", "salir"])
    code = await run_cli(read, write, factory, env={"ANTHROPIC_API_KEY": "x"})
    assert code == 2
    assert any("se cayó" in line for line in printed)
    assert factory.created[0].closed


def test_render_event_shows_blocks_reports_and_escalations_in_plain_words():
    from due_diligence.events import CallBlocked, Escalated, ReportRegistered

    blocked = render_event(CallBlocked("listas_restrictivas", "consultar_listas", "1", "falta id"))
    assert (
        "bloque" in blocked.lower() and "falta id" in blocked and "listas_restrictivas" in blocked
    )
    report = render_event(ReportRegistered("INF-0001", "CO-XX-0001", "no_habilitar"))
    assert "INF-0001" in report and "no_habilitar" in report
    escalated = render_event(Escalated("ESC-0001", "CO-XX-0001", "coincidencia en listas"))
    assert "ESC-0001" in escalated and "coincidencia en listas" in escalated
