"""Hooks de las reglas de negocio con entradas con la forma real medida con el modelo.

Medido con el SDK 0.2.168: `tool_response` de una herramienta MCP llega como texto con el sobre JSON
del servidor; el hook recibe también `agent_type` cuando lo dispara un subagente.
"""

import json

from due_diligence.rule_hooks import make_post_tool_use, make_pre_tool_use
from due_diligence.rules import CaseBook
from due_diligence.tests.test_rules import comercio, registro

PREFIX = "mcp__pasarela-fuentes__"


def pre_input(tool, tool_input, agent_type="listas_restrictivas"):
    return {
        "hook_event_name": "PreToolUse",
        "session_id": "s1",
        "transcript_path": "",
        "cwd": ".",
        "tool_name": tool if tool == "Agent" else PREFIX + tool,
        "tool_input": tool_input,
        "tool_use_id": "tu_1",
        "agent_type": agent_type,
        "agent_id": "ag_1",
    }


def post_input(tool, tool_input, response, agent_type="registro_mercantil"):
    data = pre_input(tool, tool_input, agent_type)
    data["hook_event_name"] = "PostToolUse"
    data["tool_response"] = response
    return data


def decision_of(output):
    return output.get("hookSpecificOutput", {}).get("permissionDecision")


def reason_of(output):
    return output["hookSpecificOutput"]["permissionDecisionReason"]


async def run(book, tool, tool_input, **kwargs):
    return await make_pre_tool_use(book)(pre_input(tool, tool_input, **kwargs), "tu_1", None)


async def observe(book, tool, tool_input, response, **kwargs):
    return await make_post_tool_use(book)(
        post_input(tool, tool_input, response, **kwargs), "tu_1", None
    )


# --------------------------------------------------------------------------- regla 1


async def test_the_statement_case_listas_without_identification_is_denied():
    """Caso del enunciado: consulta a listas restrictivas sin identificación unívoca, bloqueada."""
    output = await run(
        CaseBook(),
        "consultar_listas_restrictivas",
        {"tipo": "comercio", "referencia": "CO-XX-0001"},
    )
    assert decision_of(output) == "deny"
    assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert "Regla 1" in reason_of(output)
    assert "registro mercantil" in reason_of(output)


async def test_after_a_unique_registry_result_listas_is_allowed_for_commerce_and_representative():
    book = CaseBook()
    assert (
        await observe(
            book, "consultar_registro_mercantil", {"consulta": "CO-XX-0001"}, registro([comercio()])
        )
        == {}
    )
    assert (
        await run(
            book, "consultar_listas_restrictivas", {"tipo": "comercio", "referencia": "CO-XX-0001"}
        )
        == {}
    )
    assert (
        await run(
            book, "consultar_listas_restrictivas", {"tipo": "persona", "referencia": "PE-0001"}
        )
        == {}
    )


async def test_an_ambiguous_registry_result_does_not_open_listas():
    book = CaseBook()
    ambiguous = registro([comercio("CO-XX-0004"), comercio("CO-XX-0005")])
    await observe(book, "consultar_registro_mercantil", {"consulta": "Aurora"}, ambiguous)
    output = await run(
        book, "consultar_listas_restrictivas", {"tipo": "comercio", "referencia": "CO-XX-0004"}
    )
    assert decision_of(output) == "deny" and "Regla 1" in reason_of(output)


async def test_listas_for_another_commerce_is_denied_even_if_one_was_identified():
    book = CaseBook()
    await observe(
        book, "consultar_registro_mercantil", {"consulta": "CO-XX-0001"}, registro([comercio()])
    )
    output = await run(
        book, "consultar_listas_restrictivas", {"tipo": "comercio", "referencia": "CO-XX-0002"}
    )
    assert decision_of(output) == "deny"


async def test_a_malformed_listas_input_is_denied():
    output = await run(CaseBook(), "consultar_listas_restrictivas", None)
    assert decision_of(output) == "deny"


class _Exploding(CaseBook):
    def check_listas(self, tool_input):
        raise RuntimeError("fallo interno")


async def test_an_internal_error_in_a_rule_hook_denies_instead_of_allowing():
    output = await run(
        _Exploding(),
        "consultar_listas_restrictivas",
        {"tipo": "comercio", "referencia": "CO-XX-0001"},
    )
    assert decision_of(output) == "deny"
    assert "fallo interno" in reason_of(output) or "falló" in reason_of(output)


async def test_tools_that_are_not_governed_by_the_rules_are_left_to_the_isolation_guard():
    assert await run(CaseBook(), "buscar_noticias", {"consulta": "x"}, agent_type="noticias") == {}
    assert (
        await run(
            CaseBook(),
            "consultar_riesgo_categoria",
            {"categoria": "x"},
            agent_type="riesgo_categoria",
        )
        == {}
    )
    assert (
        await run(
            CaseBook(), "Agent", {"subagent_type": "noticias", "prompt": "x"}, agent_type=None
        )
        == {}
    )


async def test_the_post_hook_never_raises_and_never_blocks_whatever_it_receives():
    book = CaseBook()
    for response in (
        None,
        7,
        "basura",
        [],
        {},
        json.dumps({"ok": True, "content": "no es un objeto"}),
    ):
        assert (
            await observe(book, "consultar_registro_mercantil", {"consulta": "x"}, response) == {}
        )
    broken = post_input("consultar_registro_mercantil", None, None)
    del broken["tool_input"]
    assert await make_post_tool_use(book)(broken, None, None) == {}
    assert await make_post_tool_use(book)({}, None, None) == {}
    # y nada de lo anterior abrió las listas
    output = await run(
        book, "consultar_listas_restrictivas", {"tipo": "comercio", "referencia": "CO-XX-0001"}
    )
    assert decision_of(output) == "deny"


# --------------------------------------------------------------------------- regla 2

from due_diligence.tests.test_rules import informe, lista_resp  # noqa: E402


async def observe_clean_listas(book, comercio_id="CO-XX-0001", representante_id="PE-0001"):
    """Listas consultadas sin coincidencia (ticket #4: habilitar exige haberlas consultado)."""
    for tipo, referencia in (("comercio", comercio_id), ("persona", representante_id)):
        await observe(
            book,
            "consultar_listas_restrictivas",
            {"tipo": tipo, "referencia": referencia},
            lista_resp(False),
            agent_type="listas_restrictivas",
        )


INFORME = "registrar_informe"
ESCALAR = "escalar_a_cumplimiento"


async def identified_with_match(subject, referencia):
    book = CaseBook()
    await observe(
        book, "consultar_registro_mercantil", {"consulta": "CO-XX-0001"}, registro([comercio()])
    )
    await observe(
        book,
        "consultar_listas_restrictivas",
        {"tipo": subject, "referencia": referencia},
        lista_resp(True),
        agent_type="listas_restrictivas",
    )
    return book


async def test_habilitar_is_denied_with_rule_2_after_a_match_of_the_commerce():
    book = await identified_with_match("comercio", "CO-XX-0001")
    output = await run(book, INFORME, informe("habilitar"), agent_type=None)
    assert decision_of(output) == "deny" and "Regla 2" in reason_of(output)
    assert "escalar_a_cumplimiento" in reason_of(output)


async def test_habilitar_is_denied_after_a_match_of_the_representative_only():
    book = await identified_with_match("persona", "PE-0001")
    output = await run(book, INFORME, informe("habilitar"), agent_type=None)
    assert decision_of(output) == "deny" and "Regla 2" in reason_of(output)


async def test_escalating_and_not_enabling_are_allowed_after_a_match():
    book = await identified_with_match("comercio", "CO-XX-0001")
    resumen = {
        "comercio_id": "CO-XX-0001",
        "hallazgos": {"listas": {"fuente": "listas_ficticias", "fecha": "2026-10-16"}},
        "cobertura": {"x": 1},
        "causa": "Coincidencia en listas restrictivas.",
        "accion_recomendada": "Revisar el caso.",
    }
    assert await run(book, ESCALAR, resumen, agent_type=None) == {}
    assert await run(book, INFORME, informe("escalar_a_cumplimiento"), agent_type=None) == {}
    assert await run(book, INFORME, informe("no_habilitar"), agent_type=None) == {}


async def test_without_a_match_habilitar_is_not_denied_by_rule_2():
    book = CaseBook()
    await observe(
        book, "consultar_registro_mercantil", {"consulta": "CO-XX-0001"}, registro([comercio()])
    )
    await observe_clean_listas(book)
    assert await run(book, INFORME, informe("habilitar"), agent_type=None) == {}


# --------------------------------------------------------------------------- regla 3

from due_diligence.rule_hooks import make_user_prompt_submit  # noqa: E402
from due_diligence.tests.test_rules import riesgo_resp  # noqa: E402


async def prompt(book, text):
    data = {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "s1",
        "transcript_path": "",
        "cwd": ".",
        "prompt": text,
    }
    return await make_user_prompt_submit(book)(data, None, None)


async def test_a_category_declared_by_the_analyst_is_read_from_the_prompt_and_denies_habilitar():
    book = CaseBook()
    assert await prompt(book, "Due diligence de CO-XX-0001, venta de suplementos dietarios") == {}
    registry = registro([comercio(categoria="librería")])
    await observe(book, "consultar_registro_mercantil", {"consulta": "CO-XX-0001"}, registry)
    output = await run(book, INFORME, informe("habilitar"), agent_type=None)
    assert decision_of(output) == "deny" and "Regla 3" in reason_of(output)
    assert "oficial de cumplimiento" in reason_of(output)


async def test_a_catalog_answer_of_sin_clasificar_for_a_listed_category_still_denies():
    book = CaseBook()
    await prompt(book, "Due diligence de CO-XX-0001")
    registry = registro([comercio(categoria="librería")])
    await observe(book, "consultar_registro_mercantil", {"consulta": "CO-XX-0001"}, registry)
    await observe(
        book,
        "consultar_riesgo_categoria",
        {"categoria": "suplementos dietarios (venta en línea)"},
        riesgo_resp("suplementos dietarios (venta en línea)", "sin_clasificar"),
        agent_type="riesgo_categoria",
    )
    output = await run(book, INFORME, informe("habilitar"), agent_type=None)
    assert decision_of(output) == "deny" and "Regla 3" in reason_of(output)


async def test_the_registry_category_denies_and_escalating_stays_allowed():
    book = CaseBook()
    registry = registro([comercio(categoria="casa de apuestas")])
    await observe(book, "consultar_registro_mercantil", {"consulta": "CO-XX-0001"}, registry)
    assert decision_of(await run(book, INFORME, informe("habilitar"), agent_type=None)) == "deny"
    resumen = {
        "comercio_id": "CO-XX-0001",
        "hallazgos": {"registro": {"fuente": "registro_ficticio", "fecha": "2026-10-16"}},
        "cobertura": {"x": 1},
        "causa": "Categoría de alto riesgo.",
        "accion_recomendada": "Revisar el caso.",
    }
    assert await run(book, ESCALAR, resumen, agent_type=None) == {}


async def test_a_low_risk_commerce_is_not_denied_by_rule_3():
    book = CaseBook()
    await prompt(book, "Due diligence de Libros del Faro, CO-XX-0001")
    registry = registro([comercio(categoria="librería")])
    await observe(book, "consultar_registro_mercantil", {"consulta": "CO-XX-0001"}, registry)
    await observe(
        book,
        "consultar_riesgo_categoria",
        {"categoria": "librería"},
        riesgo_resp("librería", "bajo"),
        agent_type="riesgo_categoria",
    )
    await observe_clean_listas(book)
    assert await run(book, INFORME, informe("habilitar"), agent_type=None) == {}


async def test_the_prompt_hook_never_raises_whatever_it_receives():
    book = CaseBook()
    for data in ({}, {"prompt": None}, {"prompt": 5}, {"hook_event_name": "UserPromptSubmit"}):
        assert await make_user_prompt_submit(book)(data, None, None) == {}


# --------------------------------------------------------------------------- escalamiento y rastro

from due_diligence.rule_hooks import make_stop  # noqa: E402
from due_diligence.tests.test_rules import ESCALAR_ERROR, ESCALAR_OK  # noqa: E402


async def stop(book, active=False):
    data = {"hook_event_name": "Stop", "session_id": "s1", "cwd": ".", "stop_hook_active": active}
    return await make_stop(book)(data, None, None)


async def test_stop_is_blocked_once_while_a_commerce_with_a_match_is_not_escalated():
    book = await identified_with_match("comercio", "CO-XX-0001")
    output = await stop(book)
    assert output["decision"] == "block"
    assert "escalar_a_cumplimiento" in output["reason"] and "CO-XX-0001" in output["reason"]


async def test_stop_is_allowed_after_a_successful_escalation():
    book = await identified_with_match("comercio", "CO-XX-0001")
    await observe(
        book, "escalar_a_cumplimiento", {"comercio_id": "CO-XX-0001"}, ESCALAR_OK, agent_type=None
    )
    assert await stop(book) == {}


async def test_a_rejected_escalation_keeps_the_stop_blocked():
    book = await identified_with_match("comercio", "CO-XX-0001")
    await observe(
        book,
        "escalar_a_cumplimiento",
        {"comercio_id": "CO-XX-0001"},
        ESCALAR_ERROR,
        agent_type=None,
    )
    assert (await stop(book))["decision"] == "block"


async def test_the_stop_demand_is_made_only_once_per_closing():
    book = await identified_with_match("comercio", "CO-XX-0001")
    assert (await stop(book))["decision"] == "block"
    assert await stop(book, active=True) == {}  # ya se exigió: no se entra en un bucle


async def test_a_low_risk_commerce_never_blocks_the_closing():
    book = CaseBook()
    await observe(
        book, "consultar_registro_mercantil", {"consulta": "CO-XX-0001"}, registro([comercio()])
    )
    assert await stop(book) == {}


async def test_the_stop_hook_never_traps_the_conversation_on_an_internal_error():
    class Broken(CaseBook):
        def pending_escalations(self):
            raise RuntimeError("x")

    assert await stop(Broken()) == {}


async def test_the_trace_records_the_rule_of_each_decision(tmp_path, monkeypatch):
    import json as _json

    trace = tmp_path / "trace.jsonl"
    monkeypatch.setenv("PASARELA_HOOK_TRACE", str(trace))
    await run(
        CaseBook(),
        "consultar_listas_restrictivas",
        {"tipo": "comercio", "referencia": "CO-XX-0001"},
    )
    book = await identified_with_match("comercio", "CO-XX-0001")
    await run(book, INFORME, informe("habilitar"), agent_type=None)
    await run(book, INFORME, informe("no_habilitar"), agent_type=None)
    rows = [_json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
    assert [(r["decision"], r["rule"]) for r in rows[:2]] == [("deny", "1"), ("deny", "2")]
    assert rows[-1]["decision"] == "allow" and rows[-1]["rule"] is None


async def test_the_stop_demand_names_the_rule_that_applies():
    listas_match = await identified_with_match("persona", "PE-0001")
    assert "regla 2" in (await stop(listas_match))["reason"]
    book = CaseBook()
    registry = registro([comercio(categoria="criptoactivos")])
    await observe(book, "consultar_registro_mercantil", {"consulta": "CO-XX-0001"}, registry)
    assert "regla 3" in (await stop(book))["reason"]


# --------------------------------------------------------------------------- cobertura (#4)

from due_diligence.rule_hooks import make_post_tool_use_failure  # noqa: E402
from due_diligence.tests.test_rules_cobertura import (  # noqa: E402
    NOTICIAS,
    declared,
    error_resp,
    informe_con,
)

NEWS_INPUT = {"consulta": "Comercio de prueba SAS"}


async def fail_news(book, retryable=True, tool_input=None):
    return await observe(
        book,
        NOTICIAS,
        tool_input or NEWS_INPUT,
        error_resp(retryable=retryable),
        agent_type="noticias",
    )


async def call_news(book, tool_input=None):
    return await run(book, NOTICIAS, tool_input or NEWS_INPUT, agent_type="noticias")


async def test_a_failed_source_may_be_retried_once_and_not_twice():
    book = CaseBook()
    await fail_news(book)
    assert await call_news(book) == {}  # el reintento
    await fail_news(book)
    output = await call_news(book)
    assert decision_of(output) == "deny"
    assert "noticias" in reason_of(output) and "sin cubrir" in reason_of(output)


async def test_a_non_retryable_failure_is_never_retried():
    book = CaseBook()
    await fail_news(book, retryable=False)
    output = await call_news(book)
    assert decision_of(output) == "deny"
    assert "no es reintentable" in reason_of(output)


async def test_a_recovered_retry_allows_calling_again():
    book = CaseBook()
    await fail_news(book)
    await observe(
        book,
        NOTICIAS,
        NEWS_INPUT,
        json.dumps({"ok": True, "content": {"noticias": []}, "metadata": {}}),
        agent_type="noticias",
    )
    await fail_news(book)
    assert await call_news(book) == {}


async def test_the_retry_cap_governs_the_four_source_tools_and_leaves_the_others_alone():
    book = CaseBook()
    for tool, tool_input in (
        ("consultar_registro_mercantil", {"consulta": "x"}),
        ("consultar_listas_restrictivas", {"tipo": "comercio", "referencia": "CO-XX-0001"}),
        ("buscar_noticias", {"consulta": "x"}),
        ("consultar_riesgo_categoria", {"categoria": "x"}),
    ):
        await observe(book, tool, tool_input, error_resp(retryable=False), agent_type="x")
        output = await run(book, tool, tool_input, agent_type=None)
        assert decision_of(output) == "deny", tool
    assert await run(book, "Agent", {"prompt": "x"}, agent_type=None) == {}


async def test_an_informe_that_omits_the_failed_front_is_denied_and_declaring_it_is_allowed():
    book = CaseBook()
    await observe(
        book, "consultar_registro_mercantil", {"consulta": "CO-XX-0001"}, registro([comercio()])
    )
    await observe_clean_listas(book)
    await prompt(book, "Due diligence de CO-XX-0001")
    await fail_news(book)
    omit = await run(book, INFORME, informe_con("no_habilitar", {}), agent_type=None)
    assert decision_of(omit) == "deny"
    assert "noticias" in reason_of(omit)
    declare = informe_con("no_habilitar", declared("noticias"))
    assert await run(book, INFORME, declare, agent_type=None) == {}


async def test_two_commerces_with_different_failures_do_not_mix():
    book = CaseBook()
    for cid, rep in (("CO-XX-0001", "PE-0001"), ("CO-XX-0002", "PE-0002")):
        await observe(
            book,
            "consultar_registro_mercantil",
            {"consulta": cid},
            registro([comercio(cid, rep)]),
        )
    await observe(
        book,
        "consultar_listas_restrictivas",
        {"tipo": "comercio", "referencia": "CO-XX-0002"},
        error_resp(),
        agent_type="listas_restrictivas",
    )
    ok_one = informe_con("no_habilitar", {"x": 1}, "CO-XX-0001")
    bad_two = informe_con("no_habilitar", {"x": 1}, "CO-XX-0002")
    assert await run(book, INFORME, ok_one, agent_type=None) == {}
    assert decision_of(await run(book, INFORME, bad_two, agent_type=None)) == "deny"


async def test_escalating_without_declaring_the_failed_front_is_denied():
    book = CaseBook()
    await observe(
        book, "consultar_registro_mercantil", {"consulta": "CO-XX-0001"}, registro([comercio()])
    )
    await prompt(book, "Due diligence de CO-XX-0001")
    await fail_news(book)
    book.commerces["CO-XX-0001"].alto_riesgo = True  # escalar exige un motivo (#6)
    completo = {
        "hallazgos": {
            "registro": {"contenido": "x", "fuente": "registro_ficticio", "fecha": "2026-10-16"}
        },
        "causa": "Categoría de alto riesgo.",
        "accion_recomendada": "Revisar el caso.",
    }
    sin = {"comercio_id": "CO-XX-0001", "cobertura": {}, **completo}
    assert decision_of(await run(book, ESCALAR, sin, agent_type=None)) == "deny"
    con = {"comercio_id": "CO-XX-0001", "cobertura": declared("noticias"), **completo}
    assert await run(book, ESCALAR, con, agent_type=None) == {}


async def test_the_stop_hook_still_demands_escalation_once_with_a_failed_front():
    book = await identified_with_match("comercio", "CO-XX-0001")
    await fail_news(book)
    assert (await stop(book))["decision"] == "block"
    assert await stop(book, active=True) == {}


async def test_an_unreadable_coverage_state_denies_habilitar_fail_closed():
    book = CaseBook()
    await observe(
        book, "consultar_registro_mercantil", {"consulta": "CO-XX-0001"}, registro([comercio()])
    )
    await observe_clean_listas(book)
    book.commerces["CO-XX-0001"].fallos = None  # estado corrupto
    output = await run(book, INFORME, informe("habilitar"), agent_type=None)
    assert decision_of(output) == "deny"
    assert "no pudo evaluarse" in reason_of(output)


def failure_input(tool, tool_input, error="MCP server closed", agent_type="noticias"):
    data = pre_input(tool, tool_input, agent_type)
    data.update({"hook_event_name": "PostToolUseFailure", "error": error, "is_interrupt": False})
    return data


async def test_a_call_that_fails_without_an_envelope_is_recorded_as_a_failed_front():
    book = CaseBook()
    hook = make_post_tool_use_failure(book)
    assert await hook(failure_input(NOTICIAS, NEWS_INPUT), "tu_1", None) == {}
    failed = book.failed_fronts(None)
    assert set(failed) == {"noticias"}
    assert failed["noticias"].retryable is False
    assert decision_of(await call_news(book)) == "deny"


async def test_the_failure_hook_never_raises_and_ignores_other_tools():
    book = CaseBook()
    hook = make_post_tool_use_failure(book)
    for data in ({}, {"tool_name": None}, failure_input("Agent", {"prompt": "x"}), None, 5):
        assert await hook(data, None, None) == {}  # type: ignore[arg-type]
    assert book.failed_fronts(None) == {}


# ------------------------------------------------------- #5: procedencia, conflictos y ambigüedad
# Protección contra regresiones de extremo a extremo: `PreToolUse` ya llama a `check_informe` y
# `check_escalar`, así que estas pruebas pasan al escribirlas; lo que prueban es la integración con
# el sobre real (texto JSON con `metadata`) y con la traza de reglas.

from due_diligence.tests.test_rules_procedencia import (  # noqa: E402
    DOS_FECHAS,
    SRC_NOTICIAS,
    SRC_REGISTRO,
    comercio_con_fuentes,
    conflicto_de,
    hallazgo,
    registro_resp,
    sobre,
)
from due_diligence.tests.test_rules_procedencia import informe_con as informe_campos  # noqa: E402

BUSQUEDA = {"consulta": "Ferretería Horizonte"}


async def observe_registro_resp(book, *matches):
    return await observe(
        book,
        "consultar_registro_mercantil",
        BUSQUEDA,
        registro_resp(list(matches)),
        agent_type="registro_mercantil",
    )


async def test_one_date_of_a_conflicting_commerce_is_denied_and_both_dates_are_allowed():
    book = CaseBook()
    await observe_registro_resp(book, comercio_con_fuentes("CO-XX-0006", "PE-0006"))
    una = informe("no_habilitar", "CO-XX-0006")
    output = await run(book, INFORME, una, agent_type=None)
    assert decision_of(output) == "deny"
    assert "fecha_constitucion" in reason_of(output)
    ambas = {**una, "conflictos": [conflicto_de(*DOS_FECHAS)]}
    assert await run(book, INFORME, ambas, agent_type=None) == {}


async def test_the_conflict_of_one_commerce_is_not_required_of_another_in_the_hooks():
    book = CaseBook()
    await observe_registro_resp(book, comercio_con_fuentes("CO-XX-0006", "PE-0006"))
    await observe_registro_resp(book, comercio("CO-XX-0001", "PE-0001"))
    assert await run(book, INFORME, informe("no_habilitar", "CO-XX-0001"), agent_type=None) == {}
    output = await run(book, INFORME, informe("no_habilitar", "CO-XX-0006"), agent_type=None)
    assert decision_of(output) == "deny"


async def test_an_ambiguous_registry_result_denies_the_report_and_the_escalation_of_a_candidate():
    book = CaseBook()
    await observe_registro_resp(book, comercio("CO-XX-0004", "PE-0004"), comercio("CO-XX-0005"))
    for recomendacion in ("habilitar", "no_habilitar", "escalar_a_cumplimiento"):
        output = await run(book, INFORME, informe(recomendacion, "CO-XX-0004"), agent_type=None)
        assert decision_of(output) == "deny", recomendacion
        assert "identificador" in reason_of(output)
    escalar = {"comercio_id": "CO-XX-0005", "cobertura": {"x": 1}}
    assert decision_of(await run(book, ESCALAR, escalar, agent_type=None)) == "deny"


async def test_after_the_identifier_the_chosen_commerce_is_allowed_in_the_hooks():
    book = CaseBook()
    await observe_registro_resp(book, comercio("CO-XX-0004", "PE-0004"), comercio("CO-XX-0005"))
    await observe_registro_resp(book, comercio("CO-XX-0004", "PE-0004"))
    assert await run(book, INFORME, informe("no_habilitar", "CO-XX-0004"), agent_type=None) == {}
    other = await run(book, INFORME, informe("no_habilitar", "CO-XX-0005"), agent_type=None)
    assert decision_of(other) == "deny"


async def test_a_finding_that_cites_a_source_that_was_not_consulted_is_denied_in_the_hooks():
    book = CaseBook()
    await observe(
        book,
        "buscar_noticias",
        {"consulta": "x"},
        sobre({"noticias": []}, SRC_NOTICIAS),
        agent_type="noticias",
    )
    mala = informe_campos("no_habilitar", hallazgos={"noticias": hallazgo("diario_ficticio")})
    output = await run(book, INFORME, mala, agent_type=None)
    assert decision_of(output) == "deny"
    assert "noticias" in reason_of(output) and SRC_NOTICIAS in reason_of(output)
    buena = informe_campos("no_habilitar", hallazgos={"noticias": hallazgo(SRC_NOTICIAS)})
    assert await run(book, INFORME, buena, agent_type=None) == {}
    escalar = {"comercio_id": "CO-XX-0001", "hallazgos": mala["hallazgos"], "cobertura": {"x": 1}}
    assert decision_of(await run(book, ESCALAR, escalar, agent_type=None)) == "deny"


async def test_the_trace_records_the_new_rules(tmp_path, monkeypatch):
    trace = tmp_path / "trace.jsonl"
    monkeypatch.setenv("PASARELA_HOOK_TRACE", str(trace))
    book = CaseBook()
    await observe_registro_resp(book, comercio_con_fuentes("CO-XX-0006", "PE-0006"))
    await observe_registro_resp(book, comercio("CO-XX-0004", "PE-0004"), comercio("CO-XX-0005"))
    mala = informe_campos("no_habilitar", hallazgos={"registro": hallazgo("diario_ficticio")})
    await run(book, INFORME, informe("no_habilitar", "CO-XX-0006"), agent_type=None)
    await run(book, INFORME, informe("no_habilitar", "CO-XX-0004"), agent_type=None)
    await run(book, INFORME, {**mala, "comercio_id": "CO-XX-0001"}, agent_type=None)
    rows = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
    assert [r["rule"] for r in rows] == ["conflicto", "ambiguedad", "procedencia"]
    assert all(r["decision"] == "deny" for r in rows)


async def test_an_unreadable_state_denies_the_report_fail_closed():
    book = CaseBook()
    await observe_registro_resp(book, comercio("CO-XX-0004", "PE-0004"), comercio("CO-XX-0005"))
    book.candidates = None  # estado corrupto
    output = await run(book, INFORME, informe("no_habilitar", "CO-XX-0001"), agent_type=None)
    assert decision_of(output) == "deny"
    assert "no pudo evaluarse" in reason_of(output)
    assert SRC_REGISTRO  # la fuente real del registro sigue siendo la constante de las pruebas


# ---------------------------------------------------- #6: escalamiento con criterio y handoff
# Protección contra regresiones de extremo a extremo: `PreToolUse` ya llama a `check_informe` y
# `check_escalar`; estas pruebas ejercen la integración con el sobre real y con la traza.

from due_diligence.tests.test_rules_procedencia import SRC_LISTAS  # noqa: E402


async def observe_registro_ok(book, *matches):
    return await observe(
        book,
        "consultar_registro_mercantil",
        BUSQUEDA,
        registro_resp(list(matches)),
        agent_type="registro_mercantil",
    )


async def observe_listas_ficticias(book, match, tipo="comercio", referencia="CO-XX-0001"):
    content = {"match": match, "entradas": []}
    return await observe(
        book,
        "consultar_listas_restrictivas",
        {"tipo": tipo, "referencia": referencia},
        sobre(content, SRC_LISTAS),
        agent_type="listas_restrictivas",
    )


def resumen_oficial(**campos):
    data = {
        "comercio_id": "CO-XX-0001",
        "hallazgos": {"listas": hallazgo(SRC_LISTAS)},
        "cobertura": {"x": 1},
        "causa": "Coincidencia en listas restrictivas del comercio.",
        "accion_recomendada": "Revisar el caso antes de habilitar.",
    }
    data.update(campos)
    return data


async def test_a_low_risk_commerce_without_findings_cannot_be_escalated():
    book = CaseBook()
    await observe_registro_ok(book, comercio("CO-XX-0001", "PE-0001"))
    await observe_listas_ficticias(book, False)
    await observe_listas_ficticias(book, False, "persona", "PE-0001")
    por_herramienta = await run(book, ESCALAR, resumen_oficial(), agent_type=None)
    assert decision_of(por_herramienta) == "deny"
    assert "hallazgo" in reason_of(por_herramienta) and "habilitar" in reason_of(por_herramienta)
    por_informe = await run(book, INFORME, informe("escalar_a_cumplimiento"), agent_type=None)
    assert decision_of(por_informe) == "deny"


async def test_a_list_match_allows_a_complete_summary_and_denies_an_incomplete_one():
    book = CaseBook()
    await observe_registro_ok(book, comercio("CO-XX-0001", "PE-0001"))
    await observe_listas_ficticias(book, True)
    assert await run(book, ESCALAR, resumen_oficial(), agent_type=None) == {}
    sin_hallazgo = await run(book, ESCALAR, resumen_oficial(hallazgos={}), agent_type=None)
    assert decision_of(sin_hallazgo) == "deny" and "listas" in reason_of(sin_hallazgo)
    sin_causa = await run(book, ESCALAR, resumen_oficial(causa="revisar"), agent_type=None)
    assert decision_of(sin_causa) == "deny" and "lista" in reason_of(sin_causa)


async def test_the_motive_of_one_commerce_does_not_allow_escalating_another():
    book = CaseBook()
    await observe_registro_ok(book, comercio("CO-XX-0001", "PE-0001"))
    await observe_registro_ok(book, comercio("CO-XX-0002", "PE-0002"))
    await observe_listas_ficticias(book, True, "comercio", "CO-XX-0001")
    assert await run(book, ESCALAR, resumen_oficial(), agent_type=None) == {}
    otro = await run(book, ESCALAR, resumen_oficial(comercio_id="CO-XX-0002"), agent_type=None)
    assert decision_of(otro) == "deny"


async def test_the_trace_records_the_new_escalation_rules(tmp_path, monkeypatch):
    trace = tmp_path / "trace.jsonl"
    monkeypatch.setenv("PASARELA_HOOK_TRACE", str(trace))
    book = CaseBook()
    await observe_registro_ok(book, comercio("CO-XX-0001", "PE-0001"))
    await observe_registro_ok(book, comercio("CO-XX-0002", "PE-0002"))
    await observe_listas_ficticias(book, True, "comercio", "CO-XX-0001")
    await run(book, ESCALAR, resumen_oficial(comercio_id="CO-XX-0002"), agent_type=None)
    await run(book, ESCALAR, resumen_oficial(hallazgos={}), agent_type=None)
    await run(book, ESCALAR, resumen_oficial(causa="revisar"), agent_type=None)
    rows = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
    assert [r["rule"] for r in rows] == ["escalamiento", "handoff_hallazgos", "handoff_causa"]


async def test_the_stop_hook_still_demands_escalation_once_after_a_list_match():
    book = CaseBook()
    await observe_registro_ok(book, comercio("CO-XX-0001", "PE-0001"))
    await observe_listas_ficticias(book, True)
    assert (await stop(book))["decision"] == "block"
    assert await stop(book, active=True) == {}


async def test_an_unreadable_state_denies_the_escalation_fail_closed():
    book = CaseBook()
    await observe_registro_ok(book, comercio("CO-XX-0001", "PE-0001"))
    await observe_listas_ficticias(book, True)
    book.responded = None  # estado corrupto
    output = await run(book, ESCALAR, resumen_oficial(), agent_type=None)
    assert decision_of(output) == "deny"
    assert "no pudo evaluarse" in reason_of(output)


# --------------------------------------------------------------------------- on_decision (#7)


async def test_on_decision_is_called_only_for_denials_with_the_real_rule_and_reason():
    seen = []
    hook = make_pre_tool_use(CaseBook(), on_decision=lambda data, d: seen.append((data, d)))
    denied = await hook(
        pre_input(
            "consultar_listas_restrictivas", {"tipo": "comercio", "referencia": "CO-XX-0001"}
        ),
        "tu_1",
        None,
    )
    assert decision_of(denied) == "deny"
    assert len(seen) == 1
    data, decision = seen[0]
    assert data["agent_type"] == "listas_restrictivas"
    assert decision.rule == "1" and "Regla 1" in decision.reason
    assert decision.reason == reason_of(denied)

    # una llamada ajena a las reglas o permitida no dispara nada
    assert await hook(pre_input("Agent", {"subagent_type": "noticias"}), "tu_1", None) == {}
    assert len(seen) == 1


async def test_on_decision_failing_does_not_change_the_denial():
    def boom(data, decision):
        raise RuntimeError("la interfaz falló")

    hook = make_pre_tool_use(CaseBook(), on_decision=boom)
    out = await hook(
        pre_input(
            "consultar_listas_restrictivas", {"tipo": "comercio", "referencia": "CO-XX-0001"}
        ),
        "tu_1",
        None,
    )
    assert decision_of(out) == "deny" and "Regla 1" in reason_of(out)


async def test_without_on_decision_the_behavior_is_the_same():
    args = pre_input("consultar_listas_restrictivas", {"tipo": "comercio", "referencia": "CO-1"})
    plain = await make_pre_tool_use(CaseBook())(args, "tu_1", None)
    observed = await make_pre_tool_use(CaseBook(), on_decision=lambda *_: None)(args, "tu_1", None)
    assert plain == observed


async def test_on_decision_also_hears_the_fail_closed_denial_with_the_evaluation_rule():
    book = CaseBook()

    def explota(tool_input):
        raise ValueError("fallo interno")

    book.check_listas = explota
    seen = []
    hook = make_pre_tool_use(book, on_decision=lambda data, d: seen.append(d))
    out = await hook(
        pre_input("consultar_listas_restrictivas", {"tipo": "comercio", "referencia": "CO-1"}),
        "tu_1",
        None,
    )
    assert decision_of(out) == "deny"
    assert [d.rule for d in seen] == ["evaluacion"] and "fallo interno" in seen[0].reason
