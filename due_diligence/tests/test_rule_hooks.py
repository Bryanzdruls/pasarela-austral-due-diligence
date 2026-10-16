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
    assert await run(book, ESCALAR, {"comercio_id": "CO-XX-0001"}, agent_type=None) == {}
    assert await run(book, INFORME, informe("escalar_a_cumplimiento"), agent_type=None) == {}
    assert await run(book, INFORME, informe("no_habilitar"), agent_type=None) == {}


async def test_without_a_match_habilitar_is_not_denied_by_rule_2():
    book = CaseBook()
    await observe(
        book, "consultar_registro_mercantil", {"consulta": "CO-XX-0001"}, registro([comercio()])
    )
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
    assert await run(book, ESCALAR, {"comercio_id": "CO-XX-0001"}, agent_type=None) == {}


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
    assert await run(book, INFORME, informe("habilitar"), agent_type=None) == {}


async def test_the_prompt_hook_never_raises_whatever_it_receives():
    book = CaseBook()
    for data in ({}, {"prompt": None}, {"prompt": 5}, {"hook_event_name": "UserPromptSubmit"}):
        assert await make_user_prompt_submit(book)(data, None, None) == {}
