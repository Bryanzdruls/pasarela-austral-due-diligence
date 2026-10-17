"""Cobertura de los frentes (ticket #4): estado, reintentos y declaración, sin SDK ni modelo.

Los sobres de error tienen la forma del servidor (`mcp_server/envelope.py`): el SDK los entrega a
los hooks como texto JSON. Datos ficticios: `CO-XX-000N` y `PE-000N`.
"""

import json

import pytest

from due_diligence.rules import CaseBook
from due_diligence.tests.test_rules import (
    LISTAS,
    REGISTRO,
    assert_blocked,
    comercio,
    identified,
    informe,
    lista_resp,
    listas,
    registro,
    with_listas,
)

NOTICIAS = "buscar_noticias"
RIESGO = "consultar_riesgo_categoria"
TOOL_OF = {
    "registro": REGISTRO,
    "listas": LISTAS,
    "noticias": NOTICIAS,
    "riesgo": RIESGO,
}
INPUT_OF = {
    "registro": {"consulta": "Comercio de prueba SAS"},
    "listas": {"tipo": "comercio", "referencia": "CO-XX-0001"},
    "noticias": {"consulta": "Comercio de prueba SAS"},
    "riesgo": {"categoria": "librería"},
}


def error_resp(source="fuente_ficticia", retryable=True, code="source_unavailable", partial=None):
    return json.dumps(
        {
            "ok": False,
            "source": source,
            "error_code": code,
            "retryable": retryable,
            "partial": partial or {},
        }
    )


def ok_resp(content=None):
    return json.dumps({"ok": True, "content": content or {"x": 1}, "metadata": {"source": "f"}})


def fail(book, frente, retryable=True, tool_input=None, code="source_unavailable"):
    book.observe(
        TOOL_OF[frente],
        tool_input or INPUT_OF[frente],
        error_resp(retryable=retryable, code=code),
    )


def succeed(book, frente, tool_input=None):
    if frente == "registro":
        book.observe(REGISTRO, tool_input or INPUT_OF[frente], registro([comercio()]))
    elif frente == "listas":
        book.observe(LISTAS, tool_input or INPUT_OF[frente], lista_resp(False))
    else:
        book.observe(TOOL_OF[frente], tool_input or INPUT_OF[frente], ok_resp())


def declared(*fronts, motivo="no disponible"):
    return {f: {"estado": "sin_cubrir", "motivo": motivo} for f in fronts}


def informe_con(recomendacion, cobertura, comercio_id="CO-XX-0001"):
    data = informe(recomendacion, comercio_id)
    data["cobertura"] = cobertura
    return data


def con_motivo(book, cid="CO-XX-0001"):
    """Un motivo para escalar (alto riesgo): escalar o recomendar escalar lo exige (#6)."""
    book.commerces[cid].alto_riesgo = True
    return book


def resumen_motivo(cid="CO-XX-0001", **campos):
    """Resumen completo al oficial para un comercio con el motivo de `con_motivo`."""
    data = {
        "comercio_id": cid,
        "hallazgos": {
            "registro": {"contenido": "x", "fuente": "registro_ficticio", "fecha": "2026-10-16"}
        },
        "cobertura": {"x": 1},
        "causa": "Categoría de alto riesgo.",
        "accion_recomendada": "Revisar el caso.",
    }
    data.update(campos)
    return data


def covered_listas(book, cid="CO-XX-0001", rep="PE-0001"):
    with_listas(book, "comercio", cid, False)
    if rep:
        with_listas(book, "persona", rep, False)
    return book


# --------------------------------------------------------------------------- estado (T003)


@pytest.mark.parametrize("frente", ["registro", "listas", "noticias", "riesgo"])
@pytest.mark.parametrize("retryable", [True, False])
def test_an_error_of_each_source_is_recorded_as_a_failed_front(frente, retryable):
    book = identified(comercio())
    book.start_request("Investiga CO-XX-0001")
    fail(book, frente, retryable)
    failed = book.failed_fronts("CO-XX-0001")
    assert set(failed) == {frente}, failed
    assert failed[frente].retryable is retryable


def test_a_later_success_of_the_same_subject_clears_the_failure():
    book = identified(comercio())
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias")
    succeed(book, "noticias")
    assert book.failed_fronts("CO-XX-0001") == {}


def test_a_success_of_another_subject_does_not_clear_the_failure():
    book = identified(comercio())
    book.start_request("Investiga CO-XX-0001")
    fail(book, "riesgo", tool_input={"categoria": "librería"})
    succeed(book, "riesgo", {"categoria": "otra categoría distinta"})
    assert set(book.failed_fronts("CO-XX-0001")) == {"riesgo"}


def test_the_subject_is_normalized_so_rewriting_it_is_the_same_subject():
    book = identified(comercio())
    book.start_request("Investiga CO-XX-0001")
    fail(book, "riesgo", tool_input={"categoria": "Librería"})
    succeed(book, "riesgo", {"categoria": "  libreria "})
    assert book.failed_fronts("CO-XX-0001") == {}


@pytest.mark.parametrize("frente", ["registro", "noticias"])
def test_for_registry_and_news_the_subject_is_the_front_whatever_the_query_wording(frente):
    """Con el modelo real, noticias se reintentó con tres redacciones distintas."""
    book = identified(comercio())
    book.start_request("Investiga CO-XX-0001")
    fail(book, frente, tool_input={"consulta": "Libros del Faro SAS CO-LB-0002"})
    succeed(book, frente, {"consulta": "CO-LB-0002"})  # el frente respondió con otra redacción
    assert book.failed_fronts("CO-XX-0001") == {}


def test_the_representative_listas_failing_leaves_the_front_uncovered():
    book = identified(comercio())
    with_listas(book, "comercio", "CO-XX-0001", False)
    fail(book, "listas", tool_input=listas("persona", "PE-0001"))
    assert set(book.failed_fronts("CO-XX-0001")) == {"listas"}


def test_invalid_input_also_counts_as_a_failure():
    book = identified(comercio())
    fail(book, "riesgo", code="invalid_input", retryable=False)
    assert "riesgo" in book.failed_fronts("CO-XX-0001") or "riesgo" in book.failed_fronts(None)


@pytest.mark.parametrize("response", ["texto que no es json", "{", "[]", None, 5, {"sin": "ok"}])
def test_an_unreadable_source_response_is_a_non_retryable_failure(response):
    book = identified(comercio())
    book.start_request("Investiga CO-XX-0001")
    book.observe(NOTICIAS, INPUT_OF["noticias"], response)
    failed = book.failed_fronts("CO-XX-0001")
    assert set(failed) == {"noticias"}
    assert failed["noticias"].retryable is False
    assert failed["noticias"].error_code == "ilegible"


def test_a_missing_retryable_flag_is_taken_as_false():
    book = identified(comercio())
    book.start_request("Investiga CO-XX-0001")
    book.observe(NOTICIAS, INPUT_OF["noticias"], json.dumps({"ok": False, "error_code": "x"}))
    assert book.failed_fronts("CO-XX-0001")["noticias"].retryable is False


def test_the_partial_content_of_the_error_is_kept():
    book = identified(comercio())
    book.start_request("Investiga CO-XX-0001")
    book.observe(NOTICIAS, INPUT_OF["noticias"], error_resp(partial={"titulares": ["uno"]}))
    assert book.failed_fronts("CO-XX-0001")["noticias"].obtenido == {"titulares": ["uno"]}


def test_a_listas_failure_of_the_commerce_or_its_representative_belongs_to_that_commerce():
    book = identified(comercio("CO-XX-0001", "PE-0001"), comercio("CO-XX-0002", "PE-0002"))
    fail(book, "listas", tool_input=listas("comercio", "CO-XX-0001"))
    fail(book, "listas", tool_input=listas("persona", "PE-0002"))
    assert set(book.failed_fronts("CO-XX-0001")) == {"listas"}
    assert set(book.failed_fronts("CO-XX-0002")) == {"listas"}


def test_the_failure_of_one_commerce_does_not_show_in_another():
    book = identified(comercio("CO-XX-0001", "PE-0001"), comercio("CO-XX-0002", "PE-0002"))
    fail(book, "listas", tool_input=listas("comercio", "CO-XX-0001"))
    assert book.failed_fronts("CO-XX-0002") == {}


def test_a_news_or_risk_failure_belongs_to_the_commerces_of_the_current_request():
    book = identified(comercio("CO-XX-0001", "PE-0001"), comercio("CO-XX-0002", "PE-0002"))
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias")
    fail(book, "riesgo")
    assert set(book.failed_fronts("CO-XX-0001")) == {"noticias", "riesgo"}
    assert book.failed_fronts("CO-XX-0002") == {}


def test_the_failure_of_a_commerce_persists_across_requests():
    book = identified(comercio())
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias")
    book.start_request("Ahora registra el informe de CO-XX-0001")
    assert set(book.failed_fronts("CO-XX-0001")) == {"noticias"}


def test_a_failure_before_any_identification_is_an_orphan_until_the_source_answers():
    book = CaseBook()
    book.start_request("Investiga Comercio de prueba SAS")
    fail(book, "registro")
    assert set(book.failed_fronts(None)) == {"registro"}
    assert set(book.failed_fronts("CO-XX-0099")) == {"registro"}  # cuenta para cualquier informe
    book.start_request("Otra solicitud")
    assert set(book.failed_fronts(None)) == {"registro"}  # no se pierde con la solicitud siguiente


def test_news_and_risk_failures_before_the_registry_identifies_are_adopted_by_the_commerce():
    book = CaseBook()
    book.start_request("Investiga Comercio de prueba SAS")
    fail(book, "noticias")  # corre en paralelo con el registro y falla antes de identificar
    fail(book, "riesgo")
    succeed(book, "registro")
    book.start_request("Registra el informe de CO-XX-0001")
    assert set(book.failed_fronts("CO-XX-0001")) == {"noticias", "riesgo"}


def test_an_orphan_registry_failure_is_dropped_once_the_registry_identifies_a_commerce():
    book = CaseBook()
    book.start_request("Investiga Comercio de prueba SAS")
    fail(book, "registro", tool_input={"consulta": "otra grafía"})
    succeed(book, "registro")
    assert "registro" not in book.failed_fronts("CO-XX-0001")


def test_failed_fronts_returns_the_commerce_failures_plus_the_orphans():
    book = identified(comercio())
    book.start_request("Investiga CO-XX-0001")
    fail(book, "listas", tool_input=listas("comercio", "CO-XX-0001"))
    fail(book, "registro", tool_input={"consulta": "no identificado"})
    assert set(book.failed_fronts("CO-XX-0001")) == {"listas", "registro"}


def test_observing_never_raises_with_weird_inputs():
    book = CaseBook()
    for weird in (None, 3, object(), [], {}, "{", b"bytes"):
        for tool in (REGISTRO, LISTAS, NOTICIAS, RIESGO, None, 5):
            book.observe(tool, weird, weird)  # type: ignore[arg-type]
    assert isinstance(book.failed_fronts("CO-XX-0001"), dict)


def test_front_names_of_the_rules_match_the_subagent_front_names():
    from due_diligence.events import FrontName
    from due_diligence.rules import FRENTES, front_of_alias

    assert set(FRENTES) == {"registro", "listas", "noticias", "riesgo"}
    assert {front_of_alias(f.value) for f in FrontName} == set(FRENTES)
    for name in FRENTES:
        assert front_of_alias(name) == name
    assert front_of_alias("desconocido") is None
    assert front_of_alias(None) is None


# --------------------------------------------------------------------------- reintentos (T014)


def test_a_call_without_a_previous_failure_is_always_allowed():
    book = identified(comercio())
    for frente, tool in TOOL_OF.items():
        assert book.check_fuente(tool, INPUT_OF[frente]).allowed is True


def test_a_retryable_failure_allows_exactly_one_retry():
    book = identified(comercio())
    fail(book, "noticias")
    assert book.check_fuente(NOTICIAS, INPUT_OF["noticias"]).allowed is True  # el reintento
    fail(book, "noticias")
    assert_blocked(book.check_fuente(NOTICIAS, INPUT_OF["noticias"]), rule="reintento", hint="sin")


def test_a_non_retryable_failure_is_not_retried():
    book = identified(comercio())
    fail(book, "noticias", retryable=False)
    decision = book.check_fuente(NOTICIAS, INPUT_OF["noticias"])
    assert_blocked(decision, rule="reintento", hint="no es reintentable")


def test_a_recovered_retry_clears_the_counter():
    book = identified(comercio())
    fail(book, "noticias")
    succeed(book, "noticias")
    fail(book, "noticias")
    assert book.check_fuente(NOTICIAS, INPUT_OF["noticias"]).allowed is True


def test_another_listas_subject_is_not_a_retry():
    book = identified(comercio())
    fail(book, "listas", tool_input=listas("comercio", "CO-XX-0001"))
    fail(book, "listas", tool_input=listas("comercio", "CO-XX-0001"))
    assert book.check_fuente(LISTAS, listas("persona", "PE-0001")).allowed is True


def test_rewriting_the_same_subject_with_other_case_or_accents_does_not_escape_the_cap():
    book = identified(comercio())
    fail(book, "riesgo", tool_input={"categoria": "Librería"})
    fail(book, "riesgo", tool_input={"categoria": "LIBRERIA"})
    decision = book.check_fuente(RIESGO, {"categoria": " libreria "})
    assert_blocked(decision, rule="reintento")


@pytest.mark.parametrize("frente", ["registro", "noticias"])
def test_rewording_the_query_of_registry_or_news_does_not_escape_the_cap(frente):
    book = identified(comercio())
    fail(book, frente, tool_input={"consulta": "Libros del Faro SAS CO-LB-0002"})
    fail(book, frente, tool_input={"consulta": "Libros del Faro SAS"})  # el reintento
    decision = book.check_fuente(TOOL_OF[frente], {"consulta": "CO-LB-0002"})
    assert_blocked(decision, rule="reintento")


def test_the_cap_is_per_listas_subject():
    book = identified(comercio())
    fail(book, "listas", tool_input=listas("comercio", "CO-XX-0001"))
    fail(book, "listas", tool_input=listas("comercio", "CO-XX-0001"))
    assert_blocked(book.check_fuente(LISTAS, listas("comercio", "CO-XX-0001")), rule="reintento")
    assert book.check_fuente(LISTAS, listas("persona", "PE-0001")).allowed is True


def test_a_new_request_resets_the_attempts_but_keeps_the_commerce_failure():
    book = identified(comercio())
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias")
    fail(book, "noticias")
    assert_blocked(book.check_fuente(NOTICIAS, INPUT_OF["noticias"]), rule="reintento")
    book.start_request("Reintenta las noticias de CO-XX-0001")
    assert book.check_fuente(NOTICIAS, INPUT_OF["noticias"]).allowed is True
    assert set(book.failed_fronts("CO-XX-0001")) == {"noticias"}


def test_a_non_retryable_failure_is_retried_in_a_new_request():
    book = identified(comercio())
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias", retryable=False)
    assert_blocked(book.check_fuente(NOTICIAS, INPUT_OF["noticias"]), rule="reintento")
    book.start_request("Prueba de nuevo")
    assert book.check_fuente(NOTICIAS, INPUT_OF["noticias"]).allowed is True


@pytest.mark.parametrize("tool_input", [None, {}, "x", [], 5])
def test_a_call_with_unreadable_input_has_no_known_failure_so_it_is_allowed(tool_input):
    assert CaseBook().check_fuente(NOTICIAS, tool_input).allowed is True


# --------------------------------------------------------------------------- declaración (T017)


@pytest.mark.parametrize("frente", ["registro", "listas", "noticias", "riesgo"])
@pytest.mark.parametrize("recomendacion", ["no_habilitar", "escalar_a_cumplimiento"])
def test_a_report_that_omits_a_failed_front_is_rejected_naming_it(frente, recomendacion):
    book = covered_listas(identified(comercio()))
    book.start_request("Investiga CO-XX-0001")
    fail(book, frente)
    con_motivo(book)
    decision = book.check_informe(informe_con(recomendacion, {}))
    assert_blocked(decision, rule="cobertura", hint=frente)


@pytest.mark.parametrize("frente", ["registro", "listas", "noticias", "riesgo"])
@pytest.mark.parametrize("recomendacion", ["no_habilitar", "escalar_a_cumplimiento"])
def test_a_report_that_declares_the_failed_front_is_accepted(frente, recomendacion):
    book = covered_listas(identified(comercio()))
    book.start_request("Investiga CO-XX-0001")
    fail(book, frente)
    con_motivo(book)
    assert book.check_informe(informe_con(recomendacion, declared(frente))).allowed is True


def test_declaring_the_failed_front_as_covered_is_rejected():
    book = covered_listas(identified(comercio()))
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias")
    cobertura = {"noticias": {"estado": "cubierto"}}
    assert_blocked(book.check_informe(informe_con("no_habilitar", cobertura)), rule="cobertura")


@pytest.mark.parametrize(
    "alias, frente",
    [
        ("registro_mercantil", "registro"),
        ("listas_restrictivas", "listas"),
        ("riesgo_categoria", "riesgo"),
    ],
)
def test_the_subagent_aliases_count_as_the_front(alias, frente):
    book = covered_listas(identified(comercio()))
    book.start_request("Investiga CO-XX-0001")
    fail(book, frente)
    assert book.check_informe(informe_con("no_habilitar", declared(alias))).allowed is True


@pytest.mark.parametrize(
    "cobertura",
    [
        "noticias sin cubrir",
        ["noticias"],
        {"noticias": "sin_cubrir"},
        {"noticias": {"estado": "sin cubrir"}},
        {"noticias": {"estado": "Sin_Cubrir"}},
        {"noticias": {"motivo": "no disponible"}},
        None,
        5,
    ],
)
def test_a_coverage_with_another_shape_declares_nothing(cobertura):
    book = covered_listas(identified(comercio()))
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias")
    decision = book.check_informe(informe_con("no_habilitar", cobertura))
    assert_blocked(decision, rule="cobertura", hint="noticias")


def test_declaring_more_than_needed_is_accepted():
    book = covered_listas(identified(comercio()))
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias")
    cobertura = declared("noticias", "riesgo")
    assert book.check_informe(informe_con("no_habilitar", cobertura)).allowed is True


def test_all_the_missing_fronts_are_named():
    book = covered_listas(identified(comercio()))
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias")
    fail(book, "riesgo")
    decision = book.check_informe(informe_con("no_habilitar", declared("noticias")))
    assert_blocked(decision, rule="cobertura", hint="riesgo")
    assert "noticias" not in decision.reason.lower().split("falta")[-1]


def test_an_orphan_failure_of_the_request_must_be_declared():
    book = CaseBook()
    book.start_request("Investiga Comercio de prueba SAS")
    fail(book, "registro")
    decision = book.check_informe(informe_con("no_habilitar", {}, comercio_id="CO-XX-0001"))
    assert_blocked(decision, rule="cobertura", hint="registro")
    declaration = informe_con("no_habilitar", declared("registro"), comercio_id="CO-XX-0001")
    assert book.check_informe(declaration).allowed is True


def test_a_front_recovered_by_the_retry_does_not_need_declaring():
    book = covered_listas(identified(comercio()))
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias")
    succeed(book, "noticias")
    assert book.check_informe(
        informe_con("no_habilitar", {"riesgo": {"estado": "cubierto"}})
    ).allowed


def test_the_failure_of_another_commerce_does_not_oblige_the_declaration():
    book = covered_listas(
        identified(comercio("CO-XX-0001", "PE-0001"), comercio("CO-XX-0002", "PE-0002"))
    )
    fail(book, "listas", tool_input=listas("comercio", "CO-XX-0002"))
    assert book.check_informe(informe_con("no_habilitar", {"x": 1}, "CO-XX-0001")).allowed is True
    assert_blocked(
        book.check_informe(informe_con("no_habilitar", {"x": 1}, "CO-XX-0002")), rule="cobertura"
    )


def test_escalating_requires_the_same_declaration():
    book = con_motivo(identified(comercio()))
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias")
    sin = resumen_motivo(cobertura={})
    assert_blocked(book.check_escalar(sin), rule="cobertura", hint="noticias")
    con = resumen_motivo(cobertura=declared("noticias"))
    assert book.check_escalar(con).allowed is True


@pytest.mark.parametrize("tool_input", [None, {}, "x", [], {"comercio_id": 5}])
def test_escalating_with_unreadable_input_has_no_failure_to_declare(tool_input):
    """Sin motivo rechaza la regla `escalamiento` (#6), no la cobertura."""
    decision = CaseBook().check_escalar(tool_input)
    assert decision.rule == "escalamiento"


def test_without_failures_the_old_reports_are_accepted_unchanged():
    book = covered_listas(identified(comercio()))
    assert book.check_informe(informe("habilitar")).allowed is True
    assert book.check_informe(informe_con("no_habilitar", {"x": 1})).allowed is True
    con_motivo(book)
    assert book.check_escalar(resumen_motivo()).allowed is True


# --------------------------------------------------------------------------- habilitar (T018)


def test_habilitar_without_any_listas_consulted_is_rejected():
    book = identified(comercio())
    assert_blocked(
        book.check_informe(informe("habilitar")), rule="cobertura_habilitar", hint="listas"
    )


def test_habilitar_with_only_the_commerce_consulted_is_rejected_naming_the_representative():
    book = with_listas(identified(comercio()), "comercio", "CO-XX-0001", False)
    decision = book.check_informe(informe("habilitar"))
    assert_blocked(decision, rule="cobertura_habilitar", hint="representante")


def test_habilitar_with_the_commerce_and_the_representative_consulted_is_allowed():
    assert covered_listas(identified(comercio())).check_informe(informe("habilitar")).allowed


def test_habilitar_needs_only_the_commerce_listas_when_the_registry_gave_no_representative():
    book = identified(comercio(rep=None))
    book.commerces["CO-XX-0001"].representante_id = None
    with_listas(book, "comercio", "CO-XX-0001", False)
    assert book.check_informe(informe("habilitar")).allowed is True


def test_habilitar_with_the_listas_failing_is_rejected_even_if_declared():
    book = identified(comercio())
    book.start_request("Investiga CO-XX-0001")
    fail(book, "listas", tool_input=listas("comercio", "CO-XX-0001"))
    decision = book.check_informe(informe_con("habilitar", declared("listas")))
    assert_blocked(decision, rule="cobertura_habilitar")
    assert book.check_informe(informe_con("no_habilitar", declared("listas"))).allowed is True
    con_motivo(book)  # escalar exige un motivo (#6)
    escalar = informe_con("escalar_a_cumplimiento", declared("listas"))
    assert book.check_informe(escalar).allowed is True


def test_habilitar_with_the_registry_failing_is_rejected_by_identification():
    book = CaseBook()
    book.start_request("Investiga Comercio de prueba SAS")
    fail(book, "registro")
    decision = book.check_informe(informe_con("habilitar", declared("registro")))
    assert_blocked(decision, rule="identificacion")


@pytest.mark.parametrize("frente", ["noticias", "riesgo"])
def test_news_or_risk_failing_and_declared_does_not_prevent_habilitar(frente):
    book = covered_listas(identified(comercio()))
    book.start_request("Investiga CO-XX-0001")
    fail(book, frente)
    assert book.check_informe(informe_con("habilitar", declared(frente))).allowed is True


def test_a_match_in_listas_is_still_rule_2_and_high_risk_is_still_rule_3():
    book = with_listas(identified(comercio()), "comercio", "CO-XX-0001", True)
    assert_blocked(book.check_informe(informe("habilitar")), rule="2")
    risky = covered_listas(identified(comercio(categoria="apuestas en línea")))
    assert_blocked(risky.check_informe(informe("habilitar")), rule="3")


def test_the_order_is_vocabulary_then_declaration_then_the_habilitar_rules():
    book = identified(comercio())  # listas sin consultar
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias")
    assert_blocked(book.check_informe(informe_con("Habilitar", {})), rule="vocabulario")
    assert_blocked(book.check_informe(informe_con("habilitar", {})), rule="cobertura")
    decision = book.check_informe(informe_con("habilitar", declared("noticias")))
    assert_blocked(decision, rule="cobertura_habilitar")


def test_habilitar_with_only_the_representative_consulted_is_rejected_naming_the_commerce():
    book = with_listas(identified(comercio()), "persona", "PE-0001", False)
    decision = book.check_informe(informe("habilitar"))
    assert_blocked(decision, rule="cobertura_habilitar", hint="del comercio")
    assert "representante" not in decision.reason.lower()


# --------------------------------------------------------------------------- revisión del #4


def test_a_news_success_of_another_commerce_does_not_clear_the_failure_of_this_one():
    book = identified(comercio("CO-XX-0001", "PE-0001"), comercio("CO-XX-0002", "PE-0002"))
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias")
    book.start_request("Ahora investiga CO-XX-0002")
    succeed(book, "noticias")
    assert set(book.failed_fronts("CO-XX-0001")) == {"noticias"}
    assert book.failed_fronts("CO-XX-0002") == {}
    declaration = informe_con("no_habilitar", {"riesgo": {"estado": "cubierto"}}, "CO-XX-0001")
    assert_blocked(book.check_informe(declaration), rule="cobertura", hint="noticias")


def test_a_registry_success_of_another_commerce_does_not_clear_this_one_either():
    book = identified(comercio("CO-XX-0001", "PE-0001"))
    book.start_request("Investiga CO-XX-0001")
    fail(book, "registro", tool_input={"consulta": "CO-XX-0001"})
    book.start_request("Ahora investiga CO-XX-0002")
    book.observe(
        REGISTRO, {"consulta": "CO-XX-0002"}, registro([comercio("CO-XX-0002", "PE-0002")])
    )
    assert set(book.failed_fronts("CO-XX-0001")) == {"registro"}


def test_a_retry_in_a_later_request_that_does_not_name_the_commerce_clears_its_failure():
    book = identified(comercio())
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias")
    book.start_request("Reintenta las noticias")  # el único comercio conocido es el de la solicitud
    succeed(book, "noticias")
    assert book.failed_fronts("CO-XX-0001") == {}


def test_rewriting_the_risk_category_does_not_escape_the_retry_cap():
    book = identified(comercio())
    fail(book, "riesgo", tool_input={"categoria": "apuestas"})
    fail(book, "riesgo", tool_input={"categoria": "apuestas en línea"})
    assert_blocked(book.check_fuente(RIESGO, {"categoria": "casino virtual"}), rule="reintento")


def test_a_risk_success_with_another_category_resets_the_front_attempts():
    book = identified(comercio())
    fail(book, "riesgo", tool_input={"categoria": "apuestas"})
    succeed(book, "riesgo", {"categoria": "librería"})
    fail(book, "riesgo", tool_input={"categoria": "apuestas"})
    assert book.check_fuente(RIESGO, {"categoria": "apuestas"}).allowed is True


def test_an_orphan_news_failure_survives_to_a_later_identification_and_must_be_declared():
    book = CaseBook()
    book.start_request("Investiga Comercio de prueba SAS")
    fail(book, "noticias")
    book.start_request("Reintenta el registro")
    succeed(book, "registro")  # identifica a CO-XX-0001 y adopta la falla de noticias
    declaration = informe_con("no_habilitar", {"registro": {"estado": "cubierto"}})
    assert_blocked(book.check_informe(declaration), rule="cobertura", hint="noticias")


def test_the_commerce_id_of_the_report_is_read_without_surrounding_spaces():
    book = covered_listas(identified(comercio()))
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias")
    decision = book.check_informe(informe_con("no_habilitar", {}, comercio_id=" CO-XX-0001 "))
    assert_blocked(decision, rule="cobertura", hint="noticias")
