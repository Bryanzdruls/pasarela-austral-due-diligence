import json

from claude_agent_sdk import ToolResultBlock, UserMessage

from due_diligence.events import (
    CoordinatorText,
    FrontName,
    FrontStatus,
    SubagentFinished,
    SubagentStarted,
    Translator,
    dependency_violations,
    parallelism_violations,
)
from due_diligence.tests.fakes import agent_call, assistant, result, text, tool_result

VALID = {
    "contenido": {"menciones": []},
    "metadatos": {"fuente": "noticias_ficticias", "fecha": "2026-10-16T10:00:00+00:00"},
}


def run(*messages):
    translator = Translator()
    return [event for message in messages for event in translator.translate(message)]


def finished_for(raw_content):
    events = run(
        assistant(agent_call("t1", "noticias", "encargo")),
        tool_result("t1", raw_content),
    )
    finished = [e for e in events if isinstance(e, SubagentFinished)]
    assert len(finished) == 1
    return finished[0]


def test_a_valid_response_keeps_content_and_metadata_separated():
    f = finished_for(json.dumps(VALID))
    assert f.frente is FrontName.NOTICIAS
    assert f.result.estado is FrontStatus.COMPLETO
    assert f.result.contenido == VALID["contenido"]
    assert f.result.metadatos == VALID["metadatos"]


def test_json_wrapped_in_a_code_fence_is_accepted():
    f = finished_for("```json\n" + json.dumps(VALID) + "\n```")
    assert f.result.estado is FrontStatus.COMPLETO


def test_a_response_in_list_form_is_accepted():
    events = run(
        assistant(agent_call("t1", "noticias", "e")),
        UserMessage(
            content=[
                ToolResultBlock(
                    tool_use_id="t1", content=[{"type": "text", "text": json.dumps(VALID)}]
                )
            ]
        ),
    )
    assert events[-1].result.estado is FrontStatus.COMPLETO


def test_invalid_json_is_never_marked_complete():
    f = finished_for("Encontré dos noticias, todo bien.")
    assert f.result.estado is FrontStatus.NO_ESTRUCTURADO
    assert f.result.metadatos == {}
    assert "Encontré dos noticias" in json.dumps(f.result.contenido, ensure_ascii=False)


def test_missing_source_or_date_in_metadata_is_not_structured():
    for metadatos in ({"fuente": "x"}, {"fecha": "y"}, {}, {"fuente": "", "fecha": ""}):
        f = finished_for(json.dumps({"contenido": {}, "metadatos": metadatos}))
        assert f.result.estado is FrontStatus.NO_ESTRUCTURADO, metadatos
    f = finished_for(json.dumps({"metadatos": VALID["metadatos"]}))
    assert f.result.estado is FrontStatus.NO_ESTRUCTURADO  # sin contenido


def test_a_tool_error_is_reported_as_not_completed():
    events = run(
        assistant(agent_call("t1", "noticias", "e")),
        UserMessage(content=[ToolResultBlock(tool_use_id="t1", content="boom", is_error=True)]),
    )
    assert events[-1].result.estado is FrontStatus.NO_COMPLETADO


def test_the_encargo_is_exactly_the_prompt_sent_to_the_subagent():  # SC-003
    started = run(assistant(agent_call("t1", "registro_mercantil", "Identifica CO-TV-0001")))[0]
    assert isinstance(started, SubagentStarted)
    assert started.frente is FrontName.REGISTRO_MERCANTIL
    assert started.tool_use_id == "t1"
    assert started.encargo == "Identifica CO-TV-0001"


def test_task_is_treated_as_an_alias_of_agent():
    events = run(assistant(agent_call("t1", "riesgo_categoria", "e", tool_name="Task")))
    assert isinstance(events[0], SubagentStarted)


def test_messages_from_inside_a_subagent_are_not_coordinator_text():
    assert run(assistant(text("pensando..."), parent_tool_use_id="t1")) == []
    events = run(assistant(text("Informe.")))
    assert [type(e) for e in events] == [CoordinatorText]


def test_an_unknown_subagent_type_produces_no_event():
    assert run(assistant(agent_call("t1", "general-purpose", "e"))) == []


def test_every_event_carries_a_timestamp():
    events = run(
        assistant(agent_call("t1", "noticias", "e")),
        tool_result("t1", json.dumps(VALID)),
        assistant(text("fin")),
        result(),
    )
    assert len(events) == 4
    assert all(e.timestamp for e in events)


# --- US3: paralelo y dependencia (SC-004) ---------------------------------------------


def _valid(frente):
    sources = {
        "registro_mercantil": "registro_mercantil_ficticio",
        "noticias": "noticias_ficticias",
        "riesgo_categoria": "catalogo_riesgo_ficticio",
        "listas_restrictivas": "listas_restrictivas_ficticias",
    }
    return json.dumps(
        {
            "contenido": {"frente": frente},
            "metadatos": {"fuente": sources[frente], "fecha": "2026-10-16T10:00:00+00:00"},
        }
    )


def _three_independent_calls():
    return assistant(
        agent_call("t1", "registro_mercantil", "Identifica CO-TV-0001"),
        agent_call("t2", "noticias", "Noticias de Tienda Verde SAS"),
        agent_call("t3", "riesgo_categoria", "Riesgo de suplementos dietarios"),
    )


def test_three_agent_calls_in_one_message_start_before_any_finishes():
    events = run(_three_independent_calls())
    assert [type(e) for e in events] == [SubagentStarted] * 3
    assert [e.frente for e in events] == [
        FrontName.REGISTRO_MERCANTIL,
        FrontName.NOTICIAS,
        FrontName.RIESGO_CATEGORIA,
    ]
    stamps = [e.timestamp for e in events]
    assert stamps == sorted(stamps)


def test_results_arriving_in_another_order_are_paired_by_tool_use_id():
    events = run(
        _three_independent_calls(),
        tool_result("t3", _valid("riesgo_categoria")),
        tool_result("t1", _valid("registro_mercantil")),
        tool_result("t2", _valid("noticias")),
    )
    finished = [e for e in events if isinstance(e, SubagentFinished)]
    assert [e.frente for e in finished] == [
        FrontName.RIESGO_CATEGORIA,
        FrontName.REGISTRO_MERCANTIL,
        FrontName.NOTICIAS,
    ]
    for e in finished:  # cada resultado quedó con su propio contenido
        assert e.result.contenido == {"frente": e.frente.value}


def _correct_sequence():
    return run(
        _three_independent_calls(),
        tool_result("t1", _valid("registro_mercantil")),
        assistant(agent_call("t4", "listas_restrictivas", "Verifica CO-TV-0001 y PE-0001")),
        tool_result("t2", _valid("noticias")),
        tool_result("t3", _valid("riesgo_categoria")),
        tool_result("t4", _valid("listas_restrictivas")),
    )


def test_a_correct_sequence_has_no_violations():
    events = _correct_sequence()
    assert dependency_violations(events) == []
    assert parallelism_violations(events) == []


def test_lists_started_before_the_registry_finished_is_a_violation():
    events = run(
        assistant(agent_call("t1", "registro_mercantil", "e")),
        assistant(agent_call("t4", "listas_restrictivas", "e")),
        tool_result("t1", _valid("registro_mercantil")),
    )
    violations = dependency_violations(events)
    assert len(violations) == 1 and "listas_restrictivas" in violations[0]


def test_lists_started_without_any_registry_is_a_violation():
    events = run(assistant(agent_call("t4", "listas_restrictivas", "e")))
    assert len(dependency_violations(events)) == 1


def test_independent_fronts_serialized_is_a_parallelism_violation():
    events = run(
        assistant(agent_call("t1", "registro_mercantil", "e")),
        tool_result("t1", _valid("registro_mercantil")),
        assistant(agent_call("t2", "noticias", "e")),
        tool_result("t2", _valid("noticias")),
        assistant(agent_call("t3", "riesgo_categoria", "e")),
    )
    assert len(parallelism_violations(events)) >= 1


# --- Validación estricta del resultado de frente (hallazgos de la revisión) -------------------


def test_an_empty_content_is_not_a_complete_result():
    f = finished_for(json.dumps({"contenido": {}, "metadatos": VALID["metadatos"]}))
    assert f.result.estado is FrontStatus.NO_ESTRUCTURADO


def test_the_declared_source_must_be_the_source_of_that_front():
    wrong_meta = {**VALID["metadatos"], "fuente": "registro_mercantil_ficticio"}
    wrong = {"contenido": {"x": 1}, "metadatos": wrong_meta}
    f = finished_for(json.dumps(wrong))  # el frente es noticias
    assert f.result.estado is FrontStatus.NO_ESTRUCTURADO


def test_the_date_must_be_a_real_iso_date():
    for fecha in ("ayer", "2026-13-45", "16/10/2026", ""):
        bad = {"contenido": {"x": 1}, "metadatos": {"fuente": "noticias_ficticias", "fecha": fecha}}
        assert finished_for(json.dumps(bad)).result.estado is FrontStatus.NO_ESTRUCTURADO, fecha


def test_prose_before_the_json_object_is_tolerated_but_still_validated():
    f = finished_for("Aquí está el resultado:\n" + json.dumps(VALID))
    assert f.result.estado is FrontStatus.COMPLETO
    f = finished_for("Aquí está el resultado:\n" + json.dumps({"contenido": {}, "metadatos": {}}))
    assert f.result.estado is FrontStatus.NO_ESTRUCTURADO


def test_extra_blocks_in_the_tool_result_do_not_hide_a_valid_json_block():
    events = run(
        assistant(agent_call("t1", "noticias", "e")),
        UserMessage(
            content=[
                ToolResultBlock(
                    tool_use_id="t1",
                    content=[
                        {"type": "text", "text": json.dumps(VALID)},
                        {"type": "text", "text": "agentId: abc123 (usage: 1234 tokens)"},
                    ],
                )
            ]
        ),
    )
    assert events[-1].result.estado is FrontStatus.COMPLETO
    assert events[-1].result.contenido == VALID["contenido"]


def test_dependency_requires_a_complete_registry_result():
    events = run(
        assistant(agent_call("t1", "registro_mercantil", "e")),
        tool_result("t1", "no pude estructurar esto"),  # el registro terminó mal formado
        assistant(agent_call("t4", "listas_restrictivas", "e")),
    )
    violations = dependency_violations(events)
    assert len(violations) == 1 and "completo" in violations[0]


def test_retrying_a_front_is_not_a_parallelism_violation():
    events = run(
        _three_independent_calls(),
        tool_result("t1", "mal formado"),
        assistant(agent_call("t5", "registro_mercantil", "reintento")),  # reintento legítimo
        tool_result("t2", _valid("noticias")),
        tool_result("t3", _valid("riesgo_categoria")),
        tool_result("t5", _valid("registro_mercantil")),
    )
    assert parallelism_violations(events) == []


# --- #4: error estructurado de un frente -------------------------------------------------


def _error(frente="noticias", **changes):
    data = {
        "estado": "error",
        "frente": frente,
        "reintentable": True,
        "obtenido": {},
        "metadatos": {"fuente": "noticias_ficticias", "fecha": "2026-10-16T10:00:00+00:00"},
    }
    data.update(changes)
    return json.dumps(data)


def test_a_structured_error_is_a_failed_front_with_what_was_obtained_and_retryability():
    f = finished_for(_error(obtenido={"titulares": ["uno"]}, motivo="servicio caído"))
    assert f.result.estado is FrontStatus.FALLIDO
    assert f.result.contenido["error"] == {
        "reintentable": True,
        "obtenido": {"titulares": ["uno"]},
        "motivo": "servicio caído",
    }
    assert f.result.metadatos == {
        "fuente": "noticias_ficticias",
        "fecha": "2026-10-16T10:00:00+00:00",
    }


def test_a_structured_error_without_the_retryable_flag_is_taken_as_not_retryable():
    data = json.loads(_error())
    del data["reintentable"]
    f = finished_for(json.dumps(data))
    assert f.result.estado is FrontStatus.FALLIDO
    assert f.result.contenido["error"]["reintentable"] is False


def test_a_structured_error_wrapped_in_a_code_fence_is_accepted():
    f = finished_for("```json\n" + _error() + "\n```")
    assert f.result.estado is FrontStatus.FALLIDO


def test_an_error_for_another_front_is_not_structured():
    f = finished_for(_error(frente="registro_mercantil"))  # se delegó a noticias
    assert f.result.estado is FrontStatus.NO_ESTRUCTURADO


def test_an_error_with_a_non_boolean_retryable_or_bad_metadata_is_not_structured():
    assert finished_for(_error(reintentable="si")).result.estado is FrontStatus.NO_ESTRUCTURADO
    bad_source = {"fuente": "otra", "fecha": "2026-10-16T10:00:00+00:00"}
    assert finished_for(_error(metadatos=bad_source)).result.estado is FrontStatus.NO_ESTRUCTURADO
    assert finished_for(_error(metadatos={})).result.estado is FrontStatus.NO_ESTRUCTURADO
    assert finished_for(_error(obtenido="nada")).result.estado is FrontStatus.NO_ESTRUCTURADO


def test_a_response_without_any_known_shape_is_still_not_structured_and_the_old_shape_holds():
    assert finished_for("algo sin forma").result.estado is FrontStatus.NO_ESTRUCTURADO
    assert finished_for(json.dumps(VALID)).result.estado is FrontStatus.COMPLETO
    other_state = json.dumps({**VALID, "estado": "ok"})
    assert finished_for(other_state).result.estado is FrontStatus.COMPLETO


def test_lists_does_not_start_after_a_failed_registry():
    events = run(
        assistant(agent_call("t1", "registro_mercantil", "e")),
        tool_result(
            "t1",
            _error(
                frente="registro_mercantil",
                metadatos={
                    "fuente": "registro_mercantil_ficticio",
                    "fecha": "2026-10-16T10:00:00+00:00",
                },
            ),
        ),
        assistant(agent_call("t4", "listas_restrictivas", "e")),
    )
    violations = dependency_violations(events)
    assert len(violations) == 1 and "completo" in violations[0]


def test_the_web_events_are_immutable_timestamped_and_part_of_the_domain_union():
    import dataclasses
    import typing

    import pytest

    from due_diligence.events import CallBlocked, DomainEvent, Escalated, ReportRegistered

    blocked = CallBlocked("listas_restrictivas", "consultar_listas_restrictivas", "1", "motivo")
    report = ReportRegistered("INF-0001", "CO-XX-0001", "no_habilitar")
    escalated = Escalated("ESC-0001", "CO-XX-0001", "coincidencia en listas")
    members = typing.get_args(DomainEvent)
    for event in (blocked, report, escalated):
        assert type(event) in members
        assert event.timestamp
        with pytest.raises(dataclasses.FrozenInstanceError):
            event.timestamp = "otra"  # type: ignore[misc]
    assert (blocked.agente, blocked.regla, blocked.motivo) == ("listas_restrictivas", "1", "motivo")
    assert (report.informe_id, report.recomendacion) == ("INF-0001", "no_habilitar")
    assert (escalated.escalamiento_id, escalated.causa) == ("ESC-0001", "coincidencia en listas")
