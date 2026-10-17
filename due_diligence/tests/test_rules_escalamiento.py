"""Escalamiento con criterio y handoff (ticket #6): motivos y reglas puras, sin SDK ni modelo.

Datos ficticios: `CO-XX-000N`, `PE-000N` y fuentes terminadas en `_ficticio`/`_ficticia`.
"""

import json

import pytest

from due_diligence.rules import CaseBook
from due_diligence.tests.test_rules import (
    LISTAS,
    assert_blocked,
    comercio,
    consult_catalog,
    identified,
    informe,
    listas,
    with_clean_listas,
)
from due_diligence.tests.test_rules_procedencia import (
    DOS_FECHAS,
    NOTICIAS,
    SRC_LISTAS,
    SRC_NOTICIAS,
    SRC_REGISTRO,
    SRC_RIESGO,
    comercio_con_fuentes,
    conflicto_de,
    hallazgo,
    observe_registro,
    sobre,
)

CID = "CO-XX-0001"


def con_registro(**campos):
    """`CO-XX-0001` identificado por el registro con la fuente real del servidor."""
    return observe_registro(CaseBook(), comercio(**campos))


def coincidencia(book, tipo="comercio", referencia=CID):
    entrada = {"nombre_lista": "lista_ficticia", "fecha_inclusion": "2025-01-01"}
    content = {"match": True, "entradas": [entrada]}
    book.observe(LISTAS, listas(tipo, referencia), sobre(content, SRC_LISTAS))
    return book


def menciones(book, hay=True):
    content = {"menciones": [{"titular": "Titular ficticio"}] if hay else []}
    book.observe(NOTICIAS, {"consulta": "x"}, sobre(content, SRC_NOTICIAS))
    return book


def limpio(book):
    """Listas del comercio y de su representante sin coincidencias, con la fuente real."""
    for tipo, referencia in (("comercio", CID), ("persona", "PE-0001")):
        content = {"match": False, "entradas": []}
        book.observe(LISTAS, listas(tipo, referencia), sobre(content, SRC_LISTAS))
    return book


def motivos(book, comercio_id=CID):
    return set(book.escalation_grounds(comercio_id))


# --------------------------------------------------------------------------- menciones (T002)


def test_a_news_response_with_mentions_marks_the_commerces_of_the_request():
    book = identified(comercio("CO-XX-0001", "PE-0001"), comercio("CO-XX-0002", "PE-0002"))
    book.start_request("Investiga CO-XX-0001")
    menciones(book)
    assert book.commerces["CO-XX-0001"].menciones is True
    assert book.commerces["CO-XX-0002"].menciones is False


def test_an_empty_or_failed_news_response_marks_nothing():
    from due_diligence.tests.test_rules_cobertura import error_resp

    book = identified(comercio())
    book.start_request("Investiga CO-XX-0001")
    menciones(book, hay=False)
    book.observe(NOTICIAS, {"consulta": "x"}, error_resp())
    book.observe(NOTICIAS, {"consulta": "x"}, "texto que no es json")
    assert book.commerces[CID].menciones is False


def test_mentions_that_arrive_before_the_identification_go_to_the_first_commerce_identified():
    book = CaseBook()
    book.start_request("Investiga Comercio de prueba SAS")
    menciones(book)  # corre en paralelo con el registro
    observe_registro(book, comercio())
    book.start_request("Prepara el informe")
    assert book.commerces[CID].menciones is True


def test_the_mentions_persist_across_requests():
    book = identified(comercio())
    book.start_request("Investiga CO-XX-0001")
    menciones(book)
    book.start_request("¿Escalamos?")
    assert book.commerces[CID].menciones is True


# --------------------------------------------------------------------------- motivos (T002)


def test_a_commerce_without_findings_has_no_grounds():
    assert motivos(limpio(con_registro())) == set()


@pytest.mark.parametrize("tipo, referencia", [("comercio", CID), ("persona", "PE-0001")])
def test_a_list_match_of_the_commerce_or_its_representative_is_a_ground(tipo, referencia):
    assert motivos(coincidencia(con_registro(), tipo, referencia)) == {"listas"}


@pytest.mark.parametrize(
    "categoria", ["apuestas", "criptoactivos", "suplementos dietarios", "venta de medicamentos"]
)
def test_each_high_risk_category_of_the_registry_is_a_ground(categoria):
    assert motivos(con_registro(categoria=categoria)) == {"riesgo"}


def test_the_catalog_and_the_request_are_grounds_of_high_risk_too():
    book = con_registro()
    consult_catalog(book, "casino", "alto")
    assert motivos(book) == {"riesgo"}
    solicitud = CaseBook()
    solicitud.start_request("Due diligence de CO-XX-0001, casa de apuestas")
    observe_registro(solicitud, comercio())
    assert motivos(solicitud) == {"riesgo"}


def test_a_contradiction_flagged_by_the_registry_is_a_ground():
    book = observe_registro(CaseBook(), comercio_con_fuentes("CO-XX-0006", "PE-0006"))
    assert motivos(book, "CO-XX-0006") == {"conflicto"}


def test_mentions_are_a_ground():
    book = con_registro()
    book.start_request("Investiga CO-XX-0001")
    assert motivos(menciones(book)) == {"noticias"}


def test_several_grounds_come_together():
    book = coincidencia(con_registro(categoria="apuestas"))
    book.start_request("Investiga CO-XX-0001")
    assert motivos(menciones(book)) == {"listas", "riesgo", "noticias"}


def test_an_incomplete_coverage_is_not_a_ground():
    from due_diligence.tests.test_rules_cobertura import fail

    book = limpio(con_registro())
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias")
    fail(book, "listas", tool_input=listas("comercio", CID))
    assert motivos(book) == set()


def test_an_unidentified_commerce_has_a_ground_only_if_the_request_declares_high_risk():
    assert motivos(CaseBook(), "CO-XX-0099") == set()
    declarado = CaseBook()
    declarado.start_request("Quiero habilitar una casa de apuestas")
    assert motivos(declarado, "CO-XX-0099") == {"riesgo"}


@pytest.mark.parametrize("escrito", ["co-xx-0001", " CO-XX-0001 ", "Co-Xx-0001"])
def test_the_commerce_id_is_resolved_without_case_or_spaces(escrito):
    assert motivos(coincidencia(con_registro()), escrito) == {"listas"}


def test_the_grounds_of_one_commerce_do_not_show_in_another():
    book = observe_registro(CaseBook(), comercio("CO-XX-0001", "PE-0001"))
    observe_registro(book, comercio("CO-XX-0002", "PE-0002"))
    coincidencia(book, "comercio", "CO-XX-0001")
    assert motivos(book, "CO-XX-0001") == {"listas"}
    assert motivos(book, "CO-XX-0002") == set()


@pytest.mark.parametrize("comercio_id", [None, "", 5, [], {}])
def test_grounds_never_raise_with_a_weird_commerce_id(comercio_id):
    assert isinstance(CaseBook().escalation_grounds(comercio_id), dict)


def test_observing_news_never_raises_with_weird_payloads():
    book = identified(comercio())
    for weird in (None, 3, [], {}, "{", {"ok": True}, {"ok": True, "content": {"menciones": 5}}):
        book.observe(NOTICIAS, {"consulta": "x"}, weird)
        book.observe(NOTICIAS, {"consulta": "x"}, json.dumps(weird, default=str))
    assert book.commerces[CID].menciones in (True, False)


# --------------------------------------------------------------------------- ayudas de reglas


def informe_escalar(cid=CID, **campos):
    data = informe("escalar_a_cumplimiento", cid)
    data.update(campos)
    return data


def resumen(cid=CID, **campos):
    data = {
        "comercio_id": cid,
        "hallazgos": {},
        "cobertura": {"x": 1},
        "conflictos": [],
        "causa": "revisión",
        "accion_recomendada": "revisar antes de habilitar",
    }
    data.update(campos)
    return data


def resumen_listas(**campos):
    base = {
        "hallazgos": {"listas": hallazgo(SRC_LISTAS)},
        "causa": "Coincidencia en listas restrictivas del comercio.",
    }
    base.update(campos)
    return resumen(**base)


# ----------------------------------------------------------------- escalamiento (US1, T005)


@pytest.mark.parametrize(
    "montar",
    [
        lambda: coincidencia(con_registro()),
        lambda: coincidencia(con_registro(), "persona", "PE-0001"),
        lambda: con_registro(categoria="criptoactivos"),
        lambda: menciones(con_registro()),
    ],
    ids=["comercio", "representante", "alto_riesgo", "menciones"],
)
def test_a_commerce_with_a_ground_may_be_escalated_by_the_report_and_by_the_tool(montar):
    book = montar()
    assert book.check_informe(informe_escalar()).allowed is True
    decision = book.check_escalar(resumen())
    assert decision.rule != "escalamiento"


def test_a_contradiction_is_a_ground_to_escalate():
    book = observe_registro(CaseBook(), comercio_con_fuentes("CO-XX-0006", "PE-0006"))
    declarado = informe_escalar("CO-XX-0006", conflictos=[conflicto_de(*DOS_FECHAS)])
    assert book.check_informe(declarado).allowed is True


def test_a_low_risk_commerce_without_findings_cannot_be_escalated():
    book = limpio(con_registro())
    por_herramienta = book.check_escalar(resumen())
    assert_blocked(por_herramienta, rule="escalamiento", hint="hallazgo")
    assert "habilitar" in por_herramienta.reason
    por_informe = book.check_informe(informe_escalar())
    assert_blocked(por_informe, rule="escalamiento", hint="hallazgo")


def test_an_incomplete_coverage_alone_does_not_justify_escalating():
    from due_diligence.tests.test_rules_cobertura import declared, fail

    book = limpio(con_registro())
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias")
    cobertura = declared("noticias")
    assert_blocked(book.check_escalar(resumen(cobertura=cobertura)), rule="escalamiento")
    assert_blocked(book.check_informe(informe_escalar(cobertura=cobertura)), rule="escalamiento")
    assert "no_habilitar" in book.check_informe(informe_escalar(cobertura=cobertura)).reason


def test_the_other_recommendations_of_a_low_risk_commerce_are_still_accepted():
    book = limpio(con_registro())
    assert book.check_informe(informe("habilitar", CID)).allowed is True
    assert book.check_informe(informe("no_habilitar", CID)).allowed is True


def test_an_unidentified_commerce_may_be_escalated_only_if_the_request_declares_high_risk():
    sin = CaseBook()
    assert_blocked(sin.check_escalar(resumen("CO-XX-0099")), rule="escalamiento")
    assert_blocked(sin.check_informe(informe_escalar("CO-XX-0099")), rule="escalamiento")
    declarado = CaseBook()
    declarado.start_request("Quiero habilitar una casa de apuestas")
    assert declarado.check_informe(informe_escalar("CO-XX-0099")).allowed is True
    assert declarado.check_escalar(resumen("CO-XX-0099")).rule != "escalamiento"


@pytest.mark.parametrize("escrito", ["co-xx-0001", " CO-XX-0001 "])
def test_the_commerce_id_in_another_spelling_resolves_to_the_commerce(escrito):
    book = coincidencia(con_registro())
    assert book.check_informe(informe_escalar(escrito)).allowed is True
    sin = limpio(con_registro())
    assert_blocked(sin.check_informe(informe_escalar(escrito)), rule="escalamiento")


def test_the_ground_of_one_commerce_does_not_allow_escalating_another():
    book = observe_registro(CaseBook(), comercio("CO-XX-0001", "PE-0001"))
    observe_registro(book, comercio("CO-XX-0002", "PE-0002"))
    coincidencia(book, "comercio", "CO-XX-0001")
    assert book.check_informe(informe_escalar("CO-XX-0001")).allowed is True
    assert_blocked(book.check_informe(informe_escalar("CO-XX-0002")), rule="escalamiento")


def test_the_escalation_rule_comes_after_ambiguity_and_before_coverage():
    from due_diligence.tests.test_rules_cobertura import fail

    book = observe_registro(CaseBook(), comercio("CO-XX-0004"), comercio("CO-XX-0005"))
    assert_blocked(book.check_informe(informe_escalar("CO-XX-0004")), rule="ambiguedad")
    sin = limpio(con_registro())
    sin.start_request("Investiga CO-XX-0001")
    fail(sin, "noticias")  # cobertura sin declarar: la falta fundamental es no tener motivo
    assert_blocked(sin.check_informe(informe_escalar()), rule="escalamiento")
    assert_blocked(sin.check_escalar(resumen()), rule="escalamiento")


def test_a_corrupt_commerce_state_raises_so_the_hook_can_fail_closed():
    book = con_registro()
    book.commerces[CID].listas = None  # estado corrupto
    with pytest.raises(Exception):  # noqa: B017 - el hook convierte cualquier excepción en denegación
        book.check_informe(informe_escalar())


def test_habilitar_with_a_list_match_is_still_rule_2_and_the_stop_demand_is_unchanged():
    book = coincidencia(con_registro())
    with_clean_listas(book, CID, "PE-0001")
    assert_blocked(book.check_informe(informe("habilitar", CID)), rule="2")
    assert book.pending_escalations() == [CID]


# ------------------------------------------------------------- handoff (US2, T009)


def registro_riesgo(book):
    book.observe(
        "consultar_riesgo_categoria",
        {"categoria": "apuestas"},
        sobre({"categoria": "apuestas", "riesgo": "alto"}, SRC_RIESGO),
    )
    return book


def test_a_complete_summary_for_a_list_match_is_accepted():
    book = coincidencia(con_registro())
    assert book.check_escalar(resumen_listas()).allowed is True


def test_a_summary_without_the_list_finding_is_rejected_naming_the_front():
    book = coincidencia(con_registro())
    decision = book.check_escalar(resumen_listas(hallazgos={}))
    assert_blocked(decision, rule="handoff_hallazgos", hint="listas")
    assert "fuente" in decision.reason.lower()


@pytest.mark.parametrize(
    "clave", ["listas restrictivas", "Listas-Restrictivas", "listas_restrictivas"]
)
def test_the_front_of_the_finding_may_be_written_in_another_spelling(clave):
    book = coincidencia(con_registro())
    data = resumen_listas(hallazgos={clave: hallazgo(SRC_LISTAS)})
    assert book.check_escalar(data).allowed is True


@pytest.mark.parametrize("frente, fuente", [("registro", SRC_REGISTRO), ("riesgo", SRC_RIESGO)])
def test_a_high_risk_may_be_backed_by_the_registry_or_the_risk_finding(frente, fuente):
    book = registro_riesgo(con_registro(categoria="apuestas"))
    data = resumen(hallazgos={frente: hallazgo(fuente)}, causa="Categoría de alto riesgo.")
    assert book.check_escalar(data).allowed is True


def test_a_high_risk_without_any_registry_or_risk_finding_is_rejected():
    book = con_registro(categoria="apuestas")
    decision = book.check_escalar(resumen(causa="Categoría de alto riesgo."))
    assert_blocked(decision, rule="handoff_hallazgos", hint="riesgo")


def test_a_high_risk_only_declared_by_the_analyst_needs_no_front_finding():
    book = CaseBook()
    book.start_request("Quiero habilitar una casa de apuestas")
    data = resumen("CO-XX-0099", causa="Alto riesgo declarado por el analista")
    assert book.check_escalar(data).allowed is True


def test_mentions_require_the_news_finding_and_a_cause_that_names_them():
    book = con_registro()
    book.start_request("Investiga CO-XX-0001")
    menciones(book)
    sin = resumen(hallazgos={}, causa="Mención en noticias del comercio")
    assert_blocked(book.check_escalar(sin), rule="handoff_hallazgos", hint="noticias")
    con = resumen(hallazgos={"noticias": hallazgo(SRC_NOTICIAS)}, causa="Menciones en noticias.")
    assert book.check_escalar(con).allowed is True


@pytest.mark.parametrize("causa", ["revisar", "Caso a revisar por el oficial", "", "   "])
def test_a_cause_that_does_not_name_the_ground_is_rejected(causa):
    book = coincidencia(con_registro())
    decision = book.check_escalar(resumen_listas(causa=causa))
    assert_blocked(decision, rule="handoff_causa", hint="lista")


@pytest.mark.parametrize("causa", [None, [], 5, {"causa": "listas"}])
def test_a_cause_that_is_not_text_is_rejected(causa):
    book = coincidencia(con_registro())
    assert_blocked(book.check_escalar(resumen_listas(causa=causa)), rule="handoff_causa")


@pytest.mark.parametrize(
    "causa", ["COINCIDENCIA EN LISTAS", "Coincidencia en Lístas restrictivas", "lista restrictiva"]
)
def test_the_cause_is_compared_without_case_or_accents(causa):
    book = coincidencia(con_registro())
    assert book.check_escalar(resumen_listas(causa=causa)).allowed is True


def test_with_two_grounds_the_cause_must_name_both():
    book = coincidencia(con_registro(categoria="apuestas"))
    hallazgos = {"listas": hallazgo(SRC_LISTAS), "registro": hallazgo(SRC_REGISTRO)}
    solo_una = resumen(hallazgos=hallazgos, causa="Coincidencia en listas restrictivas.")
    assert_blocked(book.check_escalar(solo_una), rule="handoff_causa", hint="riesgo")
    ambas = resumen(hallazgos=hallazgos, causa="Coincidencia en listas y alto riesgo.")
    assert book.check_escalar(ambas).allowed is True


def test_a_contradiction_must_be_declared_in_the_escalation_too():
    book = observe_registro(CaseBook(), comercio_con_fuentes("CO-XX-0006", "PE-0006"))
    causa = "Contradicción entre las fuentes del registro."
    sin = resumen("CO-XX-0006", causa=causa)
    assert_blocked(book.check_escalar(sin), rule="conflicto", hint="fecha_constitucion")
    incompleto = resumen("CO-XX-0006", causa=causa, conflictos=[conflicto_de(DOS_FECHAS[0])])
    assert_blocked(book.check_escalar(incompleto), rule="conflicto")
    completo = resumen("CO-XX-0006", causa=causa, conflictos=[conflicto_de(*DOS_FECHAS)])
    assert book.check_escalar(completo).allowed is True


def test_a_contradiction_cause_must_name_the_contradiction():
    book = observe_registro(CaseBook(), comercio_con_fuentes("CO-XX-0006", "PE-0006"))
    data = resumen("CO-XX-0006", causa="revisar", conflictos=[conflicto_de(*DOS_FECHAS)])
    assert_blocked(book.check_escalar(data), rule="handoff_causa", hint="contradic")


def test_the_checks_come_in_the_documented_order():
    from due_diligence.tests.test_rules_cobertura import declared, fail

    book = coincidencia(con_registro())
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias")
    mala = {"noticias": hallazgo("diario_ficticio")}
    data = resumen(hallazgos=mala, causa="revisar", cobertura={})
    assert_blocked(book.check_escalar(data), rule="cobertura")
    data = resumen(hallazgos=mala, causa="revisar", cobertura=declared("noticias"))
    assert book.check_escalar(data).allowed is False
    declarada = declared("noticias")
    sin_listas = resumen(hallazgos={}, causa="revisar", cobertura=declarada)
    assert_blocked(book.check_escalar(sin_listas), rule="handoff_hallazgos")
    con_listas = resumen(hallazgos={"listas": hallazgo(SRC_LISTAS)}, causa="revisar")
    con_listas["cobertura"] = declarada
    assert_blocked(book.check_escalar(con_listas), rule="handoff_causa")


def test_a_complete_summary_with_several_grounds_and_an_uncovered_front_is_accepted():
    from due_diligence.tests.test_rules_cobertura import declared, fail

    book = coincidencia(con_registro(categoria="apuestas"))
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias")
    data = resumen(
        hallazgos={"listas": hallazgo(SRC_LISTAS), "registro": hallazgo(SRC_REGISTRO)},
        causa="Coincidencia en listas restrictivas y categoría de alto riesgo.",
        cobertura=declared("noticias"),
    )
    assert book.check_escalar(data).allowed is True


def test_a_front_declared_uncovered_is_not_required_as_a_finding():
    from due_diligence.tests.test_rules_cobertura import declared

    book = menciones(con_registro())
    data = resumen(hallazgos={}, causa="Menciones en noticias.", cobertura=declared("noticias"))
    assert book.check_escalar(data).allowed is True


def test_a_corrupt_state_raises_so_the_hook_can_fail_closed():
    book = coincidencia(con_registro())
    book.responded = None  # estado corrupto
    with pytest.raises(Exception):  # noqa: B017 - el hook convierte cualquier excepción en denegación
        book.check_escalar(resumen_listas())
