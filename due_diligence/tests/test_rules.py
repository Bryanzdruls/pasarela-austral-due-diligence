"""Reglas de negocio 1 a 3 (ticket #3): lógica pura, sin SDK ni modelo.

Las respuestas de las herramientas tienen la forma medida con el modelo real: el servidor devuelve
el sobre JSON `{"ok":..,"content":{..},"metadata":{..}}` y el SDK lo entrega a los hooks como texto.
Datos ficticios: `CO-XX-000N` (comercios) y `PE-000N` (personas).
"""

import json

import pytest

from due_diligence.rules import (
    HIGH_RISK_ROOTS,
    RECOMMENDATIONS,
    Decision,
    is_high_risk,
    parse_envelope,
)

# --------------------------------------------------------------------------- piezas base


@pytest.mark.parametrize(
    "category",
    [
        "apuestas",
        "Casa de APUESTAS en línea",
        "criptoactivos",
        "Intercambio de Criptoactivos",
        "suplementos dietarios",
        "Venta en línea de Suplementos Dietarios",
        "venta de medicamentos",
        "VENTA DE MEDICAMENTOS CON FÓRMULA",
        "  suplemento dietario  ",
    ],
)
def test_the_four_high_risk_categories_are_detected_with_nuances(category):
    assert is_high_risk(category) is True


@pytest.mark.parametrize(
    "category", ["librería", "cafetería", "tienda de ropa", "", "   ", "servicios de software"]
)
def test_ordinary_categories_and_empty_text_are_not_high_risk(category):
    assert is_high_risk(category) is False


def test_the_high_risk_policy_is_the_pasarela_list_and_not_the_catalog():
    assert set(HIGH_RISK_ROOTS) == {"apuesta", "cripto", "suplemento", "medicament"}


def test_the_recommendation_vocabulary_is_closed_and_exact():
    assert set(RECOMMENDATIONS) == {"habilitar", "no_habilitar", "escalar_a_cumplimiento"}
    assert len(RECOMMENDATIONS) == 3


def test_a_decision_carries_the_rule_and_the_reason():
    decision = Decision(False, "1", "falta identificar al comercio")
    assert decision.allowed is False and decision.rule == "1"
    assert "identificar" in decision.reason


# --------------------------------------------------------------------------- parse_envelope

ENVELOPE = {"ok": True, "content": {"match_count": 1}, "metadata": {"source": "x"}}


def test_a_json_text_envelope_is_parsed():
    assert parse_envelope(json.dumps(ENVELOPE)) == ENVELOPE


def test_an_already_decoded_envelope_is_accepted():
    assert parse_envelope(ENVELOPE) == ENVELOPE


def test_a_list_of_text_blocks_is_unwrapped():
    blocks = [{"type": "text", "text": json.dumps(ENVELOPE)}]
    assert parse_envelope(blocks) == ENVELOPE


def test_a_dict_that_wraps_the_blocks_in_content_is_unwrapped():
    wrapped = {"content": [{"type": "text", "text": json.dumps(ENVELOPE)}]}
    assert parse_envelope(wrapped) == ENVELOPE


def test_an_error_envelope_is_still_an_envelope():
    error = {"ok": False, "source": "registro_mercantil_ficticio", "error_code": "x"}
    assert parse_envelope(json.dumps(error)) == error


@pytest.mark.parametrize(
    "response",
    [
        "esto no es json",
        "",
        None,
        42,
        "[1, 2, 3]",
        json.dumps({"content": {"match_count": 1}}),  # sin `ok`
        [{"type": "text", "text": "tampoco"}],
        [],
        {"content": [{"type": "image"}]},
    ],
)
def test_anything_that_is_not_an_envelope_is_none(response):
    assert parse_envelope(response) is None


# --------------------------------------------------------------------------- regla 1 (US1)

from due_diligence.rules import CaseBook  # noqa: E402

REGISTRO = "consultar_registro_mercantil"
LISTAS = "consultar_listas_restrictivas"


def comercio(id="CO-XX-0001", rep="PE-0001", categoria="librería", existe=True):
    return {
        "id": id,
        "razon_social": "Comercio de prueba SAS",
        "existe": existe,
        "estado": "activo",
        "representante_legal": {"id": rep, "nombre": "Persona Ficticia"},
        "categoria": categoria,
    }


def registro(matches, ok=True, ambiguous=None, match_count=None):
    """Respuesta del registro con la forma real: sobre JSON como texto."""
    content = {
        "match_count": len(matches) if match_count is None else match_count,
        "ambiguous": len(matches) > 1 if ambiguous is None else ambiguous,
        "matches": matches,
    }
    return json.dumps({"ok": ok, "content": content, "metadata": {"source": "registro_ficticio"}})


def identified(*commerces):
    """Un CaseBook que ya procesó un registro unívoco por cada comercio dado."""
    book = CaseBook()
    for c in commerces:
        book.observe(REGISTRO, {"consulta": c["id"]}, registro([c]))
    return book


def listas(tipo, referencia):
    return {"tipo": tipo, "referencia": referencia}


def assert_blocked(decision, rule="1", hint=None):
    assert decision.allowed is False, decision
    assert decision.rule == rule, decision
    assert decision.reason, "un bloqueo siempre explica qué hacer"
    if hint:
        assert hint in decision.reason.lower(), decision.reason


def test_listas_without_any_registry_result_is_blocked():
    decision = CaseBook().check_listas(listas("comercio", "CO-XX-0001"))
    assert_blocked(decision, hint="registro")


def test_listas_after_an_ambiguous_registry_result_is_blocked():
    book = CaseBook()
    book.observe(
        REGISTRO, {"consulta": "Aurora"}, registro([comercio("CO-XX-0004"), comercio("CO-XX-0005")])
    )
    assert_blocked(book.check_listas(listas("comercio", "CO-XX-0004")), hint="unívoc")
    assert_blocked(book.check_listas(listas("comercio", "CO-XX-0005")))


@pytest.mark.parametrize(
    "response",
    [
        registro([]),  # ninguna coincidencia
        json.dumps(
            {"ok": False, "source": "registro_ficticio", "error_code": "source_unavailable"}
        ),
        "esto no se puede interpretar",
        None,
        registro([comercio(existe=False)]),  # una coincidencia que no existe
        registro([comercio()], ambiguous=True),  # una coincidencia pero marcada ambigua
        registro([comercio()], match_count=2),  # contador inconsistente
    ],
)
def test_a_registry_result_that_does_not_identify_uniquely_never_opens_listas(response):
    book = CaseBook()
    book.observe(REGISTRO, {"consulta": "CO-XX-0001"}, response)
    assert_blocked(book.check_listas(listas("comercio", "CO-XX-0001")))
    assert_blocked(book.check_listas(listas("persona", "PE-0001")))


def test_a_unique_existing_match_allows_listas_for_the_commerce_and_its_representative():
    book = identified(comercio())
    assert book.check_listas(listas("comercio", "CO-XX-0001")).allowed is True
    assert book.check_listas(listas("persona", "PE-0001")).allowed is True


def test_another_commerce_or_a_person_who_is_not_the_representative_is_blocked():
    book = identified(comercio())
    assert_blocked(book.check_listas(listas("comercio", "CO-XX-0002")))
    assert_blocked(book.check_listas(listas("persona", "PE-0002")))


@pytest.mark.parametrize(
    "tool_input",
    [
        {},
        None,
        {"tipo": "comercio"},
        {"referencia": "CO-XX-0001"},
        {"tipo": "otra cosa", "referencia": "CO-XX-0001"},
        {"tipo": "comercio", "referencia": 5},
        {"tipo": "comercio", "referencia": ""},
        "no es un diccionario",
    ],
)
def test_malformed_listas_input_is_blocked_even_for_an_identified_commerce(tool_input):
    assert_blocked(identified(comercio()).check_listas(tool_input))


def test_two_commerces_do_not_mix_their_representatives():
    book = identified(comercio("CO-XX-0001", "PE-0001"), comercio("CO-XX-0002", "PE-0002"))
    assert book.check_listas(listas("persona", "PE-0001")).allowed is True
    assert book.check_listas(listas("persona", "PE-0002")).allowed is True
    only_first = identified(comercio("CO-XX-0001", "PE-0001"))
    assert_blocked(only_first.check_listas(listas("persona", "PE-0002")))


def test_a_later_unique_result_identifies_a_commerce_that_was_ambiguous_by_name():
    book = CaseBook()
    book.observe(
        REGISTRO, {"consulta": "Aurora"}, registro([comercio("CO-XX-0004"), comercio("CO-XX-0005")])
    )
    assert_blocked(book.check_listas(listas("comercio", "CO-XX-0004")))
    book.observe(
        REGISTRO, {"consulta": "CO-XX-0004"}, registro([comercio("CO-XX-0004", "PE-0004")])
    )
    assert book.check_listas(listas("comercio", "CO-XX-0004")).allowed is True
    assert_blocked(book.check_listas(listas("comercio", "CO-XX-0005")))


def test_observe_accepts_the_full_mcp_tool_name_and_never_raises():
    book = CaseBook()
    book.observe("mcp__pasarela-fuentes__" + REGISTRO, {"consulta": "x"}, registro([comercio()]))
    assert book.check_listas(listas("comercio", "CO-XX-0001")).allowed is True
    for weird in (None, 3, object(), [], {}, "{", b"bytes"):
        book.observe(REGISTRO, weird, weird)  # type: ignore[arg-type]
        book.observe(None, weird, weird)  # type: ignore[arg-type]
    assert book.check_listas(listas("comercio", "CO-XX-0001")).allowed is True


# --------------------------------------------------------------------------- regla 2 (US2)


def lista_resp(match, ok=True):
    """Respuesta de listas con la forma real (sobre JSON como texto)."""
    entradas = (
        [{"nombre_lista": "lista_ficticia", "fecha_inclusion": "2025-01-01"}] if match else []
    )
    content = {"match": match, "entradas": entradas}
    return json.dumps({"ok": ok, "content": content, "metadata": {"source": "listas_ficticias"}})


def informe(recomendacion, comercio_id="CO-XX-0001"):
    return {
        "comercio_id": comercio_id,
        "recomendacion": recomendacion,
        "hallazgos": {},
        "cobertura": {},
        "conflictos": [],
    }


def with_listas(book, tipo, referencia, match):
    book.observe(LISTAS, listas(tipo, referencia), lista_resp(match))
    return book


def with_clean_listas(book, comercio_id="CO-XX-0001", representante_id="PE-0001"):
    """Listas consultadas sin coincidencia para el comercio y su representante (ticket #4: habilitar
    exige que se hayan consultado)."""
    with_listas(book, "comercio", comercio_id, False)
    return with_listas(book, "persona", representante_id, False)


def test_a_match_of_the_commerce_in_listas_blocks_habilitar_with_rule_2():
    book = with_listas(identified(comercio()), "comercio", "CO-XX-0001", True)
    decision = book.check_informe(informe("habilitar"))
    assert_blocked(decision, rule="2", hint="escal")


def test_a_match_of_the_legal_representative_blocks_habilitar_too():
    book = identified(comercio())
    with_listas(book, "comercio", "CO-XX-0001", False)
    with_listas(book, "persona", "PE-0001", True)
    assert_blocked(book.check_informe(informe("habilitar")), rule="2", hint="representante")


def test_without_any_match_rule_2_does_not_block_habilitar():
    book = identified(comercio())
    with_listas(book, "comercio", "CO-XX-0001", False)
    with_listas(book, "persona", "PE-0001", False)
    assert book.check_informe(informe("habilitar")).allowed is True


def test_a_match_of_one_commerce_does_not_affect_another():
    book = identified(comercio("CO-XX-0001", "PE-0001"), comercio("CO-XX-0002", "PE-0002"))
    with_listas(book, "comercio", "CO-XX-0001", True)
    assert_blocked(book.check_informe(informe("habilitar", "CO-XX-0001")), rule="2")
    with_clean_listas(book, "CO-XX-0002", "PE-0002")
    assert book.check_informe(informe("habilitar", "CO-XX-0002")).allowed is True


def escalamiento_completo(causa, hallazgos, cid="CO-XX-0001"):
    """Resumen completo al oficial (ticket #6: el hallazgo del frente que motiva y la causa)."""
    return {
        "comercio_id": cid,
        "hallazgos": hallazgos,
        "cobertura": {"x": 1},
        "causa": causa,
        "accion_recomendada": "Revisar el caso.",
    }


@pytest.mark.parametrize("recomendacion", ["no_habilitar", "escalar_a_cumplimiento"])
def test_the_other_recommendations_and_escalating_are_always_allowed_with_a_match(recomendacion):
    book = with_listas(identified(comercio()), "comercio", "CO-XX-0001", True)
    assert book.check_informe(informe(recomendacion)).allowed is True
    hallazgos = {"listas": {"fuente": "listas_ficticias", "fecha": "2026-10-16"}}
    resumen = escalamiento_completo("Coincidencia en listas restrictivas.", hallazgos)
    assert book.check_escalar(resumen).allowed is True


def test_a_failed_or_unreadable_listas_result_is_not_recorded_as_no_match():
    book = identified(comercio())
    book.observe(LISTAS, listas("comercio", "CO-XX-0001"), lista_resp(False, ok=False))
    book.observe(LISTAS, listas("persona", "PE-0001"), "basura")
    assert book.commerces["CO-XX-0001"].listas == {}
    book.observe(LISTAS, listas("comercio", "CO-XX-0001"), lista_resp(False))
    assert book.commerces["CO-XX-0001"].listas == {"comercio": False}


def test_a_listas_result_for_an_unidentified_reference_creates_nothing():
    book = CaseBook()
    book.observe(LISTAS, listas("comercio", "CO-XX-0009"), lista_resp(True))
    assert book.commerces == {}


def test_a_later_clean_listas_result_never_erases_an_earlier_match():
    book = with_listas(identified(comercio()), "comercio", "CO-XX-0001", True)
    with_listas(book, "comercio", "CO-XX-0001", False)
    assert_blocked(book.check_informe(informe("habilitar")), rule="2")


# --------------------------------------------------------------------------- regla 3 (US3)

RIESGO = "consultar_riesgo_categoria"
CATEGORIES = ["apuestas", "criptoactivos", "suplementos dietarios", "venta de medicamentos"]


def riesgo_resp(categoria, riesgo, ok=True):
    content = {"categoria": categoria, "riesgo": riesgo}
    return json.dumps({"ok": ok, "content": content, "metadata": {"source": "catalogo_ficticio"}})


def consult_catalog(book, categoria, riesgo):
    book.observe(RIESGO, {"categoria": categoria}, riesgo_resp(categoria, riesgo))
    return book


@pytest.mark.parametrize("category", CATEGORIES)
def test_the_category_in_the_registry_blocks_habilitar_with_rule_3(category):
    book = identified(comercio(categoria=category))
    assert_blocked(
        book.check_informe(informe("habilitar")), rule="3", hint="oficial de cumplimiento"
    )


@pytest.mark.parametrize("category", CATEGORIES)
def test_the_category_declared_by_the_analyst_blocks_habilitar_even_if_the_registry_says_otherwise(
    category,
):
    book = CaseBook()
    book.start_request(f"Necesito el due diligence de Comercio SAS, CO-XX-0001. Es de {category}.")
    book.observe(REGISTRO, {"consulta": "CO-XX-0001"}, registro([comercio(categoria="librería")]))
    assert_blocked(book.check_informe(informe("habilitar")), rule="3")


@pytest.mark.parametrize("category", CATEGORIES)
def test_a_high_risk_category_blocks_even_when_the_catalog_answers_sin_clasificar(category):
    """En la ejecución real el catálogo devolvió sin_clasificar para suplementos en línea."""
    book = identified(comercio(categoria="librería"))
    consult_catalog(book, f"{category} (venta en línea)", "sin_clasificar")
    assert_blocked(book.check_informe(informe("habilitar")), rule="3")


def test_the_catalog_saying_alto_blocks_even_for_a_category_outside_the_pasarela_list():
    book = identified(comercio(categoria="librería"))
    consult_catalog(book, "categoría rara", "alto")
    assert_blocked(book.check_informe(informe("habilitar")), rule="3")


def test_a_low_risk_commerce_without_alerts_can_be_enabled():
    book = CaseBook()
    book.start_request("Necesito el due diligence de Libros del Faro, CO-XX-0001")
    book.observe(REGISTRO, {"consulta": "CO-XX-0001"}, registro([comercio(categoria="librería")]))
    consult_catalog(book, "librería", "bajo")
    with_clean_listas(book)
    assert book.check_informe(informe("habilitar")).allowed is True


@pytest.mark.parametrize("recomendacion", ["no_habilitar", "escalar_a_cumplimiento"])
def test_escalating_is_always_allowed_for_a_high_risk_commerce(recomendacion):
    book = identified(comercio(categoria="apuestas"))
    assert book.check_informe(informe(recomendacion)).allowed is True
    hallazgos = {"registro": {"fuente": "registro_ficticio", "fecha": "2026-10-16"}}
    resumen = escalamiento_completo("Categoría de alto riesgo.", hallazgos)
    assert book.check_escalar(resumen).allowed is True


def test_the_evidence_of_a_request_does_not_pass_to_a_low_risk_commerce_investigated_later():
    book = CaseBook()
    book.start_request("Due diligence de Tienda Verde, CO-XX-0001, suplementos dietarios")
    book.observe(
        REGISTRO,
        {"consulta": "CO-XX-0001"},
        registro([comercio("CO-XX-0001", "PE-0001", "suplementos dietarios")]),
    )
    consult_catalog(book, "suplementos dietarios", "alto")
    assert_blocked(book.check_informe(informe("habilitar", "CO-XX-0001")), rule="3")

    book.start_request("Ahora necesito el due diligence de Libros del Faro, CO-XX-0002")
    book.observe(
        REGISTRO,
        {"consulta": "CO-XX-0002"},
        registro([comercio("CO-XX-0002", "PE-0002", "librería")]),
    )
    with_clean_listas(book, "CO-XX-0002", "PE-0002")
    assert book.check_informe(informe("habilitar", "CO-XX-0002")).allowed is True

    # lo ya determinado de un comercio se conserva en las solicitudes siguientes
    book.start_request("¿Y qué dijeron las noticias de Tienda Verde?")
    assert_blocked(book.check_informe(informe("habilitar", "CO-XX-0001")), rule="3")


def test_a_declared_category_sticks_to_the_commerce_identified_in_that_request():
    book = CaseBook()
    book.start_request("Due diligence de CO-XX-0001, es una casa de apuestas")
    book.observe(REGISTRO, {"consulta": "CO-XX-0001"}, registro([comercio(categoria="librería")]))
    book.start_request("¿Lo podemos habilitar?")  # la solicitud nueva ya no menciona la categoría
    assert_blocked(book.check_informe(informe("habilitar")), rule="3")


def test_a_high_risk_result_that_arrives_after_the_registry_in_the_same_request_still_counts():
    book = CaseBook()
    book.start_request("Due diligence de CO-XX-0001")
    book.observe(REGISTRO, {"consulta": "CO-XX-0001"}, registro([comercio(categoria="librería")]))
    consult_catalog(book, "criptoactivos", "alto")  # llega después, en paralelo
    book.start_request("¿Lo habilitamos?")
    assert_blocked(book.check_informe(informe("habilitar")), rule="3")


def test_rule_2_is_reported_before_rule_3_when_both_apply():
    book = with_listas(identified(comercio(categoria="apuestas")), "comercio", "CO-XX-0001", True)
    assert_blocked(book.check_informe(informe("habilitar")), rule="2")


# ------------------------------------------------------------ vocabulario y FR-010 (US4)

ESCALAR = "escalar_a_cumplimiento"
ESCALAR_OK = json.dumps({"ok": True, "content": {"escalamiento_id": "E-0001"}, "metadata": {}})
ESCALAR_ERROR = json.dumps(
    {"ok": False, "source": "x", "error_code": "invalid_input", "retryable": False, "partial": {}}
)


@pytest.mark.parametrize(
    "recomendacion",
    ["Habilitar", "habilitar comercio", " habilitar", "HABILITAR", "", None, 5, ["habilitar"]],
)
def test_a_recommendation_outside_the_closed_vocabulary_is_rejected_listing_the_allowed_values(
    recomendacion,
):
    decision = identified(comercio()).check_informe(informe(recomendacion))
    assert_blocked(decision, rule="vocabulario")
    for allowed in ("habilitar", "no_habilitar", "escalar_a_cumplimiento"):
        assert allowed in decision.reason


@pytest.mark.parametrize("tool_input", [None, {}, "habilitar", [], {"comercio_id": "CO-XX-0001"}])
def test_an_informe_without_a_recommendation_is_rejected(tool_input):
    assert_blocked(identified(comercio()).check_informe(tool_input), rule="vocabulario")


def test_habilitar_for_a_commerce_never_identified_is_rejected():
    decision = CaseBook().check_informe(informe("habilitar", "CO-XX-0009"))
    assert_blocked(decision, rule="identificacion", hint="identificado")
    other = identified(comercio("CO-XX-0001"))
    assert_blocked(other.check_informe(informe("habilitar", "CO-XX-0002")), rule="identificacion")
    assert_blocked(other.check_informe(informe("habilitar", None)), rule="identificacion")


def test_not_enabling_does_not_need_an_identified_commerce():
    """Escalar sin comercio identificado ya no se permite sin motivo (#6: `escalamiento`)."""
    assert CaseBook().check_informe(informe("no_habilitar", "CO-XX-0009")).allowed is True


def test_a_clean_identified_commerce_can_be_enabled():
    assert with_clean_listas(identified(comercio())).check_informe(informe("habilitar")).allowed


# ------------------------------------------------------------ escalamiento pendiente (A1)


def test_a_commerce_with_a_match_in_listas_is_pending_until_it_is_escalated():
    book = with_listas(identified(comercio()), "comercio", "CO-XX-0001", True)
    assert book.pending_escalations() == ["CO-XX-0001"]
    book.observe(ESCALAR, {"comercio_id": "CO-XX-0001"}, ESCALAR_OK)
    assert book.pending_escalations() == []


def test_a_high_risk_commerce_is_pending_until_it_is_escalated():
    book = identified(comercio(categoria="criptoactivos"))
    assert book.pending_escalations() == ["CO-XX-0001"]
    book.observe(ESCALAR, {"comercio_id": "CO-XX-0001"}, ESCALAR_OK)
    assert book.pending_escalations() == []


def test_a_rejected_escalation_does_not_count_as_escalated():
    book = with_listas(identified(comercio()), "comercio", "CO-XX-0001", True)
    book.observe(ESCALAR, {"comercio_id": "CO-XX-0001"}, ESCALAR_ERROR)
    book.observe(ESCALAR, {"comercio_id": "CO-XX-0001"}, "basura")
    assert book.pending_escalations() == ["CO-XX-0001"]


def test_a_low_risk_commerce_without_matches_is_never_pending():
    book = identified(comercio(categoria="librería"))
    with_listas(book, "comercio", "CO-XX-0001", False)
    assert book.pending_escalations() == []


def test_escalating_one_commerce_does_not_clear_another():
    book = identified(
        comercio("CO-XX-0001", "PE-0001", "apuestas"), comercio("CO-XX-0002", "PE-0002", "apuestas")
    )
    book.observe(ESCALAR, {"comercio_id": "CO-XX-0001"}, ESCALAR_OK)
    assert book.pending_escalations() == ["CO-XX-0002"]


def test_the_pending_escalations_say_which_rule_applies_to_each_commerce():
    book = identified(
        comercio("CO-XX-0001", "PE-0001", "librería"), comercio("CO-XX-0002", "PE-0002", "apuestas")
    )
    with_listas(book, "persona", "PE-0001", True)
    reasons = book.escalation_reasons()
    assert set(reasons) == {"CO-XX-0001", "CO-XX-0002"}
    assert any("regla 2" in r for r in reasons["CO-XX-0001"])
    assert any("regla 3" in r for r in reasons["CO-XX-0002"])
    assert book.pending_escalations() == list(reasons)


# ------------------------------------------------------------ revisión: sin mezcla entre comercios


def test_a_later_request_about_a_high_risk_commerce_never_marks_a_clean_one():
    """Bloqueante de la revisión: la evidencia de una solicitud no pasa a comercios ajenos."""
    book = CaseBook()
    book.start_request("Due diligence de Libros del Faro, CO-XX-0001")
    book.observe(
        REGISTRO,
        {"consulta": "CO-XX-0001"},
        registro([comercio("CO-XX-0001", "PE-0001", "librería")]),
    )
    with_clean_listas(book, "CO-XX-0001", "PE-0001")
    assert book.check_informe(informe("habilitar", "CO-XX-0001")).allowed is True

    book.start_request("Ahora Tienda Verde, CO-XX-0002, suplementos dietarios")
    book.observe(
        REGISTRO, {"consulta": "CO-XX-0002"}, registro([comercio("CO-XX-0002", "PE-0002", "otro")])
    )
    assert set(book.escalation_reasons()) == {"CO-XX-0002"}  # solo el comercio de esta solicitud
    assert book.check_informe(informe("habilitar", "CO-XX-0001")).allowed is True
    assert_blocked(book.check_informe(informe("habilitar", "CO-XX-0002")), rule="3")

    book.start_request("¿Y qué dijeron las noticias?")
    assert (
        book.check_informe(informe("habilitar", "CO-XX-0001")).allowed is True
    )  # sin marca permanente
    assert_blocked(book.check_informe(informe("habilitar", "CO-XX-0002")), rule="3")


def test_a_clean_commerce_is_not_marked_by_catalog_results_of_another_request():
    book = CaseBook()
    book.start_request("Due diligence de CO-XX-0001")
    book.observe(
        REGISTRO,
        {"consulta": "CO-XX-0001"},
        registro([comercio("CO-XX-0001", "PE-0001", "librería")]),
    )
    book.start_request("Due diligence de CO-XX-0002")
    book.observe(
        REGISTRO, {"consulta": "CO-XX-0002"}, registro([comercio("CO-XX-0002", "PE-0002", "otro")])
    )
    consult_catalog(book, "criptoactivos", "alto")
    assert set(book.escalation_reasons()) == {"CO-XX-0002"}


def test_a_commerce_mentioned_by_id_in_a_later_request_takes_that_requests_declared_category():
    book = identified(comercio("CO-XX-0001", "PE-0001", "librería"))
    book.start_request("CO-XX-0001 en realidad vende apuestas en línea, ¿lo habilitamos igual?")
    assert_blocked(book.check_informe(informe("habilitar", "CO-XX-0001")), rule="3")


def test_with_a_single_known_commerce_a_follow_up_declaring_a_category_applies_to_it():
    book = identified(comercio("CO-XX-0001", "PE-0001", "librería"))
    book.start_request("Me dicen que es de criptoactivos. ¿Lo podemos habilitar?")
    assert_blocked(book.check_informe(informe("habilitar", "CO-XX-0001")), rule="3")


def test_a_category_declared_before_naming_the_commerce_is_not_lost():
    """Importante de la revisión: 'casa de apuestas' llega antes que el nombre del comercio."""
    book = CaseBook()
    book.start_request("Quiero habilitar una casa de apuestas en línea")
    book.start_request("Se llama Casa Fortuna, CO-XX-0009")
    registry = registro([comercio("CO-XX-0009", "PE-0009", "servicios")])
    book.observe(REGISTRO, {"consulta": "CO-XX-0009"}, registry)
    consult_catalog(book, "servicios", "bajo")
    assert_blocked(book.check_informe(informe("habilitar", "CO-XX-0009")), rule="3")


def test_a_carried_category_is_consumed_by_the_first_commerce_identified():
    book = CaseBook()
    book.start_request("Quiero habilitar una casa de apuestas")
    book.start_request("Se llama Uno, CO-XX-0001")
    book.observe(
        REGISTRO,
        {"consulta": "CO-XX-0001"},
        registro([comercio("CO-XX-0001", "PE-0001", "servicios")]),
    )
    book.start_request("Ahora otro, CO-XX-0002")
    book.observe(
        REGISTRO,
        {"consulta": "CO-XX-0002"},
        registro([comercio("CO-XX-0002", "PE-0002", "servicios")]),
    )
    with_clean_listas(book, "CO-XX-0002", "PE-0002")
    assert book.check_informe(informe("habilitar", "CO-XX-0002")).allowed is True
