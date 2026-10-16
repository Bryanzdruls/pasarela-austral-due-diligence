"""Procedencia, conflictos y ambigüedad (ticket #5): estado y reglas puras, sin SDK ni modelo.

Los sobres tienen la forma del servidor (`mcp_server/envelope.py`): el SDK los entrega a los hooks
como texto JSON con `content` y `metadata` (`source`, `fetched_at`). Datos ficticios: `CO-XX-000N`,
`PE-000N` y fuentes terminadas en `_ficticio`/`_ficticia`.
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
    listas,
    with_clean_listas,
)

NOTICIAS = "buscar_noticias"
RIESGO = "consultar_riesgo_categoria"
SRC_REGISTRO = "registro_mercantil_ficticio"
SRC_ALTERNA = "camara_comercio_alterna_ficticia"
SRC_LISTAS = "listas_restrictivas_ficticias"
SRC_NOTICIAS = "noticias_ficticias"
SRC_RIESGO = "catalogo_riesgo_ficticio"
FECHA = "2026-10-16T12:00:00+00:00"


def sobre(content, source, fetched_at=FECHA, ok=True):
    return json.dumps(
        {"ok": ok, "content": content, "metadata": {"source": source, "fetched_at": fetched_at}}
    )


def comercio_con_fuentes(cid="CO-XX-0006", rep="PE-0006", fechas=("2016-03-14", "2017-03-14")):
    """Un comercio del registro con dos orígenes para la fecha de constitución."""
    data = comercio(cid, rep)
    data["fuentes_registro"] = [
        {"source": SRC_REGISTRO, "fecha_constitucion": fechas[0]},
        {"source": SRC_ALTERNA, "fecha_constitucion": fechas[1]},
    ]
    data["conflicts"] = ["fecha_constitucion"] if fechas[0] != fechas[1] else []
    return data


def registro_resp(matches, ambiguous=None):
    return sobre(
        {
            "match_count": len(matches),
            "ambiguous": len(matches) > 1 if ambiguous is None else ambiguous,
            "matches": matches,
        },
        SRC_REGISTRO,
    )


def observe_registro(book, *matches, consulta="x"):
    book.observe(REGISTRO, {"consulta": consulta}, registro_resp(list(matches)))
    return book


def respondio(book, frente):
    return set(book.responded.get(frente, {}))


# --------------------------------------------------------------------------- fuentes respondidas


@pytest.mark.parametrize(
    "tool, frente, source, entrada",
    [
        (REGISTRO, "registro", SRC_REGISTRO, {"consulta": "x"}),
        (LISTAS, "listas", SRC_LISTAS, listas("comercio", "CO-XX-0001")),
        (NOTICIAS, "noticias", SRC_NOTICIAS, {"consulta": "x"}),
        (RIESGO, "riesgo", SRC_RIESGO, {"categoria": "librería"}),
    ],
)
def test_each_correct_response_records_its_source_and_date(tool, frente, source, entrada):
    book = CaseBook()
    book.observe(tool, entrada, sobre({"x": 1}, source))
    assert book.responded[frente] == {source: FECHA}


@pytest.mark.parametrize("frente", ["registro", "listas", "noticias", "riesgo"])
def test_an_error_or_an_unreadable_response_records_nothing(frente):
    from due_diligence.tests.test_rules_cobertura import INPUT_OF, TOOL_OF, error_resp

    book = CaseBook()
    book.observe(TOOL_OF[frente], INPUT_OF[frente], error_resp())
    book.observe(TOOL_OF[frente], INPUT_OF[frente], "texto que no es json")
    book.observe(TOOL_OF[frente], INPUT_OF[frente], None)
    assert book.responded.get(frente, {}) == {}


def test_the_source_is_normalized_and_a_missing_one_records_nothing():
    book = CaseBook()
    book.observe(NOTICIAS, {"consulta": "x"}, sobre({"x": 1}, "  Noticias_Ficticias "))
    book.observe(RIESGO, {"categoria": "x"}, json.dumps({"ok": True, "content": {"a": 1}}))
    book.observe(RIESGO, {"categoria": "x"}, sobre({"a": 1}, 5))
    assert respondio(book, "noticias") == {"noticias_ficticias"}
    assert respondio(book, "riesgo") == set()


def test_the_registry_also_records_the_origins_of_the_returned_matches():
    book = observe_registro(CaseBook(), comercio_con_fuentes())
    assert respondio(book, "registro") == {SRC_REGISTRO, SRC_ALTERNA}


def test_the_responded_sources_persist_across_requests_and_commerces():
    book = observe_registro(CaseBook(), comercio_con_fuentes("CO-XX-0006", "PE-0006"))
    book.start_request("Ahora otro comercio, CO-XX-0001")
    observe_registro(book, comercio("CO-XX-0001", "PE-0001"))
    assert SRC_ALTERNA in respondio(book, "registro")


# --------------------------------------------------------------------------- contradicciones


def test_a_conflict_flagged_by_the_server_keeps_every_value_with_its_origin():
    book = observe_registro(CaseBook(), comercio_con_fuentes())
    conflictos = book.commerces["CO-XX-0006"].conflictos
    assert set(conflictos) == {"fecha_constitucion"}
    assert set(conflictos["fecha_constitucion"]) == {
        ("2016-03-14", SRC_REGISTRO),
        ("2017-03-14", SRC_ALTERNA),
    }


def test_without_a_flag_or_with_the_same_value_there_is_no_conflict():
    sin_marca = comercio_con_fuentes()
    del sin_marca["conflicts"]
    assert observe_registro(CaseBook(), sin_marca).commerces["CO-XX-0006"].conflictos == {}
    igual = comercio_con_fuentes(fechas=("2016-03-14", "2016-03-14"))
    igual["conflicts"] = ["fecha_constitucion"]  # marca sin diferencia real: no hay contradicción
    assert observe_registro(CaseBook(), igual).commerces["CO-XX-0006"].conflictos == {}


def test_a_later_registry_result_recomputes_the_conflicts():
    book = observe_registro(CaseBook(), comercio_con_fuentes())
    observe_registro(book, comercio_con_fuentes(fechas=("2016-03-14", "2016-03-14")))
    assert book.commerces["CO-XX-0006"].conflictos == {}


def test_conflicts_persist_across_requests_and_do_not_show_in_another_commerce():
    book = observe_registro(CaseBook(), comercio_con_fuentes("CO-XX-0006", "PE-0006"))
    observe_registro(book, comercio("CO-XX-0001", "PE-0001"))
    book.start_request("Reporte final")
    assert book.commerces["CO-XX-0006"].conflictos
    assert book.commerces["CO-XX-0001"].conflictos == {}


@pytest.mark.parametrize(
    "fuentes",
    [None, "texto", [], [5], [{"source": SRC_REGISTRO}], [{"fecha_constitucion": "2016-03-14"}]],
)
def test_a_malformed_origin_list_never_raises_and_gives_no_conflict(fuentes):
    data = comercio_con_fuentes()
    data["fuentes_registro"] = fuentes
    book = observe_registro(CaseBook(), data)
    assert book.commerces["CO-XX-0006"].conflictos == {}


# --------------------------------------------------------------------------- candidatos


def test_an_ambiguous_registry_result_leaves_every_match_as_a_candidate_and_identifies_none():
    book = observe_registro(CaseBook(), comercio("CO-XX-0004"), comercio("CO-XX-0005"))
    assert book.candidates == {"CO-XX-0004", "CO-XX-0005"}
    assert book.commerces == {}


def test_a_unique_registry_result_by_id_identifies_the_candidate_and_removes_it():
    book = observe_registro(CaseBook(), comercio("CO-XX-0004"), comercio("CO-XX-0005"))
    observe_registro(book, comercio("CO-XX-0004"), consulta="CO-XX-0004")
    assert book.candidates == {"CO-XX-0005"}
    assert "CO-XX-0004" in book.commerces


def test_candidates_persist_across_requests():
    book = observe_registro(CaseBook(), comercio("CO-XX-0004"), comercio("CO-XX-0005"))
    book.start_request("El de la calle principal")
    assert book.candidates == {"CO-XX-0004", "CO-XX-0005"}


def test_a_unique_result_never_creates_candidates():
    assert observe_registro(CaseBook(), comercio()).candidates == set()


def test_an_identified_commerce_is_not_added_as_a_candidate_again():
    book = identified(comercio("CO-XX-0004"))
    observe_registro(book, comercio("CO-XX-0004"), comercio("CO-XX-0005"))
    assert book.candidates == {"CO-XX-0005"}


def test_matches_without_a_readable_id_are_ignored_as_candidates():
    unreadable = comercio("CO-XX-0004")
    unreadable["id"] = None
    book = observe_registro(CaseBook(), unreadable, comercio("CO-XX-0005"))
    assert book.candidates == {"CO-XX-0005"}


def test_an_error_or_an_unreadable_registry_response_creates_no_candidates():
    book = CaseBook()
    book.observe(REGISTRO, {"consulta": "x"}, "texto")
    book.observe(REGISTRO, {"consulta": "x"}, json.dumps({"ok": False, "error_code": "x"}))
    assert book.candidates == set()


def test_observing_never_raises_with_weird_registry_payloads():
    book = CaseBook()
    for weird in (None, 3, [], {}, "{", {"ok": True}, {"ok": True, "content": {"matches": 5}}):
        book.observe(REGISTRO, {"consulta": "x"}, weird)
        book.observe(REGISTRO, {"consulta": "x"}, json.dumps(weird, default=str))
    assert isinstance(book.candidates, set)
    assert isinstance(book.responded, dict)


# ----------------------------------------------------------------------- ayudas para las historias


def informe_con(recomendacion, comercio_id="CO-XX-0001", **campos):
    data = informe(recomendacion, comercio_id)
    data.update(campos)
    return data


def conflicto_de(*pares, dato="fecha_constitucion"):
    return {"dato": dato, "valores": [{"valor": v, "fuente": f} for v, f in pares]}


DOS_FECHAS = (("2016-03-14", SRC_REGISTRO), ("2017-03-14", SRC_ALTERNA))


def con_conflicto():
    """Un CaseBook con `CO-XX-0006` identificado, con dos fechas y las listas consultadas."""
    book = observe_registro(CaseBook(), comercio_con_fuentes("CO-XX-0006", "PE-0006"))
    return with_clean_listas(book, "CO-XX-0006", "PE-0006")


# --------------------------------------------------------------------------- conflicto (US2, T005)


@pytest.mark.parametrize("recomendacion", ["no_habilitar", "escalar_a_cumplimiento", "habilitar"])
@pytest.mark.parametrize("conflictos", [None, [], [conflicto_de(DOS_FECHAS[0])]])
def test_a_report_that_does_not_declare_the_whole_conflict_is_rejected_naming_the_data(
    recomendacion, conflictos
):
    book = con_conflicto()
    data = informe_con(recomendacion, "CO-XX-0006")
    if conflictos is not None:
        data["conflictos"] = conflictos
    decision = book.check_informe(data)
    assert_blocked(decision, rule="conflicto", hint="fecha_constitucion")
    assert "2017-03-14" in decision.reason or "2016-03-14" in decision.reason


def test_a_report_with_a_single_date_and_no_conflict_is_rejected():
    book = con_conflicto()
    data = informe_con(
        "no_habilitar", "CO-XX-0006", hallazgos={"datos_del_analista": {"fecha": "2016-03-14"}}
    )
    assert_blocked(book.check_informe(data), rule="conflicto")


def test_a_report_that_declares_every_value_with_its_origin_is_accepted():
    book = con_conflicto()
    data = informe_con("no_habilitar", "CO-XX-0006", conflictos=[conflicto_de(*DOS_FECHAS)])
    assert book.check_informe(data).allowed is True


def test_a_pair_without_its_origin_or_with_the_origin_of_another_value_is_rejected():
    book = con_conflicto()
    sin_origen = {
        "dato": "fecha_constitucion",
        "valores": [{"valor": "2016-03-14"}, {"valor": "2017-03-14"}],
    }
    assert_blocked(
        book.check_informe(informe_con("no_habilitar", "CO-XX-0006", conflictos=[sin_origen])),
        rule="conflicto",
    )
    cruzado = conflicto_de(("2016-03-14", SRC_ALTERNA), ("2017-03-14", SRC_REGISTRO))
    decision = book.check_informe(informe_con("no_habilitar", "CO-XX-0006", conflictos=[cruzado]))
    assert_blocked(decision, rule="conflicto")


def test_declaring_more_values_than_needed_is_accepted():
    book = con_conflicto()
    extra = conflicto_de(*DOS_FECHAS, ("2018-03-14", "otra_fuente_ficticia"))
    assert book.check_informe(informe_con("no_habilitar", "CO-XX-0006", conflictos=[extra])).allowed


@pytest.mark.parametrize(
    "dato",
    ["Fecha de Constitución", "fecha constitucion", "FECHA_CONSTITUCION", " fecha_constitucion "],
)
def test_the_data_name_is_compared_normalized(dato):
    book = con_conflicto()
    declared = conflicto_de(*DOS_FECHAS, dato=dato)
    assert book.check_informe(
        informe_con("no_habilitar", "CO-XX-0006", conflictos=[declared])
    ).allowed


def test_the_origin_may_carry_decorations_but_must_name_the_source():
    book = con_conflicto()
    decorado = conflicto_de(
        ("2016-03-14", f"{SRC_REGISTRO} (consultado 2026-10-16)"),
        ("2017-03-14", SRC_ALTERNA.upper()),
    )
    assert book.check_informe(
        informe_con("no_habilitar", "CO-XX-0006", conflictos=[decorado])
    ).allowed


@pytest.mark.parametrize(
    "conflictos",
    [
        "conflicto de fechas",
        {"dato": "fecha_constitucion"},
        ["fecha_constitucion"],
        [{"dato": "fecha_constitucion", "valores": "2016-03-14 y 2017-03-14"}],
        [{"dato": "fecha_constitucion", "valores": [5, None]}],
        5,
    ],
)
def test_a_conflict_declared_with_another_shape_declares_nothing(conflictos):
    book = con_conflicto()
    data = informe_con("no_habilitar", "CO-XX-0006", conflictos=conflictos)
    assert_blocked(book.check_informe(data), rule="conflicto")


def test_the_conflict_of_another_commerce_is_not_required():
    book = con_conflicto()
    observe_registro(book, comercio("CO-XX-0001", "PE-0001"))
    assert book.check_informe(informe_con("no_habilitar", "CO-XX-0001")).allowed is True


def test_a_commerce_without_contradictions_is_accepted_with_empty_conflicts():
    book = with_clean_listas(identified(comercio()))
    assert book.check_informe(informe_con("habilitar", conflictos=[])).allowed is True


def test_the_conflict_is_still_required_in_a_later_request():
    book = con_conflicto()
    book.start_request("Prepara el informe final")
    assert_blocked(book.check_informe(informe_con("no_habilitar", "CO-XX-0006")), rule="conflicto")


def test_the_report_of_an_unidentified_commerce_requires_no_conflicts():
    book = con_conflicto()
    assert book.check_informe(informe_con("no_habilitar", "CO-XX-0099")).allowed is True


def test_the_conflict_check_runs_after_coverage_and_before_the_habilitar_rules():
    book = con_conflicto()
    book.start_request("Investiga CO-XX-0006")
    book.observe(
        NOTICIAS,
        {"consulta": "x"},
        json.dumps(
            {"ok": False, "error_code": "source_unavailable", "retryable": True, "partial": {}}
        ),
    )
    sin_declarar = informe_con("habilitar", "CO-XX-0006")
    assert_blocked(book.check_informe(sin_declarar), rule="cobertura")
    cobertura = {"noticias": {"estado": "sin_cubrir", "motivo": "no disponible"}}
    assert_blocked(
        book.check_informe(informe_con("habilitar", "CO-XX-0006", cobertura=cobertura)),
        rule="conflicto",
    )


def test_an_unreadable_conflict_state_raises_so_the_hook_can_fail_closed():
    book = con_conflicto()
    book.commerces["CO-XX-0006"].conflictos = None  # estado corrupto
    with pytest.raises(Exception):  # noqa: B017 - el hook convierte cualquier excepción en denegación
        book.check_informe(informe_con("no_habilitar", "CO-XX-0006"))


# ------------------------------------------------------------------------- ambigüedad (US3, T010)


def ambiguo():
    """Dos comercios de nombre casi idéntico: el registro devuelve ambos."""
    return observe_registro(
        CaseBook(), comercio("CO-XX-0004", "PE-0004"), comercio("CO-XX-0005", "PE-0005")
    )


def escalamiento(comercio_id, **campos):
    return {"comercio_id": comercio_id, "cobertura": {"x": 1}, **campos}


@pytest.mark.parametrize("candidato", ["CO-XX-0004", "CO-XX-0005"])
@pytest.mark.parametrize("recomendacion", ["habilitar", "no_habilitar", "escalar_a_cumplimiento"])
def test_a_report_in_the_name_of_an_unidentified_candidate_is_rejected(candidato, recomendacion):
    decision = ambiguo().check_informe(informe_con(recomendacion, candidato))
    assert_blocked(decision, rule="ambiguedad", hint="identificador")
    assert "CO-XX-0004" in decision.reason and "CO-XX-0005" in decision.reason


@pytest.mark.parametrize("candidato", ["CO-XX-0004", "CO-XX-0005"])
def test_escalating_in_the_name_of_an_unidentified_candidate_is_rejected(candidato):
    assert_blocked(ambiguo().check_escalar(escalamiento(candidato)), rule="ambiguedad")


def test_after_the_identifier_the_chosen_commerce_is_accepted_and_the_other_stays_rejected():
    book = ambiguo()
    observe_registro(book, comercio("CO-XX-0004", "PE-0004"), consulta="CO-XX-0004")
    assert book.check_informe(informe_con("no_habilitar", "CO-XX-0004")).allowed is True
    assert book.check_escalar(escalamiento("CO-XX-0004")).allowed is True
    assert_blocked(book.check_informe(informe_con("no_habilitar", "CO-XX-0005")), rule="ambiguedad")


def test_the_ambiguity_persists_in_the_next_request():
    book = ambiguo()
    book.start_request("El de la calle principal")
    assert_blocked(book.check_informe(informe_con("no_habilitar", "CO-XX-0004")), rule="ambiguedad")


def test_a_commerce_that_is_not_a_candidate_is_not_affected_even_if_unidentified():
    assert ambiguo().check_informe(informe_con("no_habilitar", "CO-XX-0099")).allowed is True


def test_the_commerce_id_is_read_without_surrounding_spaces():
    decision = ambiguo().check_informe(informe_con("no_habilitar", " CO-XX-0004 "))
    assert_blocked(decision, rule="ambiguedad")


def test_a_unique_registry_result_has_no_ambiguity():
    book = observe_registro(CaseBook(), comercio())
    assert book.check_informe(informe_con("no_habilitar")).allowed is True


def test_ambiguity_is_reported_before_coverage_and_the_habilitar_rules():
    from due_diligence.tests.test_rules_cobertura import error_resp

    book = ambiguo()
    book.start_request("Investiga CO-XX-0004")
    book.observe(NOTICIAS, {"consulta": "x"}, error_resp())
    assert_blocked(book.check_informe(informe_con("habilitar", "CO-XX-0004")), rule="ambiguedad")
    assert_blocked(book.check_escalar(escalamiento("CO-XX-0004")), rule="ambiguedad")


def test_a_corrupt_candidate_state_raises_so_the_hook_can_fail_closed():
    book = ambiguo()
    book.candidates = None  # estado corrupto
    with pytest.raises(Exception):  # noqa: B017 - el hook convierte cualquier excepción en denegación
        book.check_informe(informe_con("no_habilitar", "CO-XX-0004"))


# ------------------------------------------------------------------------ procedencia (US1, T015)


def hallazgo(fuente, fecha=FECHA, **campos):
    return {"contenido": "dato", "fuente": fuente, "fecha": fecha, **campos}


def con_fuentes():
    """`CO-XX-0001` identificado, con las cuatro fuentes respondidas y las listas limpias."""
    book = observe_registro(CaseBook(), comercio("CO-XX-0001", "PE-0001"))
    book.observe(LISTAS, listas("comercio", "CO-XX-0001"), sobre({"match": False}, SRC_LISTAS))
    book.observe(LISTAS, listas("persona", "PE-0001"), sobre({"match": False}, SRC_LISTAS))
    book.observe(NOTICIAS, {"consulta": "x"}, sobre({"noticias": []}, SRC_NOTICIAS))
    book.observe(RIESGO, {"categoria": "librería"}, sobre({"riesgo": "bajo"}, SRC_RIESGO))
    return book


def con_hallazgos(recomendacion="no_habilitar", **hallazgos):
    return informe_con(recomendacion, hallazgos=hallazgos)


@pytest.mark.parametrize(
    "frente, fuente",
    [
        ("registro", SRC_REGISTRO),
        ("listas", SRC_LISTAS),
        ("noticias", SRC_NOTICIAS),
        ("riesgo", SRC_RIESGO),
    ],
)
def test_a_finding_that_cites_the_source_that_responded_is_accepted(frente, fuente):
    assert con_fuentes().check_informe(con_hallazgos(**{frente: hallazgo(fuente)})).allowed is True


def test_a_finding_that_cites_a_source_that_was_not_consulted_is_rejected_naming_the_front():
    decision = con_fuentes().check_informe(con_hallazgos(noticias=hallazgo("diario_ficticio")))
    assert_blocked(decision, rule="procedencia", hint="noticias")
    assert SRC_NOTICIAS in decision.reason


def test_a_finding_that_cites_the_source_of_another_front_is_rejected():
    decision = con_fuentes().check_informe(con_hallazgos(noticias=hallazgo(SRC_LISTAS)))
    assert_blocked(decision, rule="procedencia", hint="noticias")


@pytest.mark.parametrize("fuente", [None, "", "   ", 5, {"nombre": SRC_NOTICIAS}])
def test_a_finding_without_a_readable_source_is_rejected(fuente):
    decision = con_fuentes().check_informe(con_hallazgos(noticias=hallazgo(fuente)))
    assert_blocked(decision, rule="procedencia", hint="legible")


@pytest.mark.parametrize("clave", ["fecha", "fecha_consulta", "fetched_at"])
def test_the_date_is_accepted_under_any_of_its_three_names(clave):
    entrada = {"contenido": "dato", "fuente": SRC_NOTICIAS, clave: "2026-10-16"}
    assert con_fuentes().check_informe(con_hallazgos(noticias=entrada)).allowed is True


@pytest.mark.parametrize("fecha", [None, "", "  "])
def test_a_finding_without_a_date_is_rejected(fecha):
    entrada = {"contenido": "dato", "fuente": SRC_NOTICIAS}
    if fecha is not None:
        entrada["fecha"] = fecha
    decision = con_fuentes().check_informe(con_hallazgos(noticias=entrada))
    assert_blocked(decision, rule="procedencia", hint="fecha")


@pytest.mark.parametrize(
    "fuente",
    [
        f"{SRC_NOTICIAS} (consultado el 2026-10-16)",
        SRC_NOTICIAS.upper(),
        "Noticias_Ficticias",
        [SRC_NOTICIAS],
        [SRC_NOTICIAS, f"{SRC_NOTICIAS} otra vez"],
    ],
)
def test_the_source_may_carry_decorations_or_be_a_list_of_real_sources(fuente):
    assert con_fuentes().check_informe(con_hallazgos(noticias=hallazgo(fuente))).allowed is True


def test_a_list_of_sources_is_rejected_if_one_of_them_did_not_respond():
    mixta = hallazgo([SRC_NOTICIAS, "diario_ficticio"])
    assert_blocked(con_fuentes().check_informe(con_hallazgos(noticias=mixta)), rule="procedencia")


def test_an_origin_of_the_registry_is_a_valid_source_for_the_registry_front():
    book = observe_registro(CaseBook(), comercio_con_fuentes("CO-XX-0006", "PE-0006"))
    data = informe_con(
        "no_habilitar",
        "CO-XX-0006",
        hallazgos={"registro": hallazgo(SRC_ALTERNA)},
        conflictos=[conflicto_de(*DOS_FECHAS)],
    )
    assert book.check_informe(data).allowed is True


@pytest.mark.parametrize(
    "clave, fuente",
    [
        ("registro_mercantil", SRC_REGISTRO),
        ("riesgo_categoria", SRC_RIESGO),
        ("listas_restrictivas", SRC_LISTAS),
    ],
)
def test_the_subagent_aliases_are_checked_like_the_front(clave, fuente):
    assert con_fuentes().check_informe(con_hallazgos(**{clave: hallazgo(fuente)})).allowed is True
    decision = con_fuentes().check_informe(con_hallazgos(**{clave: hallazgo("diario_ficticio")}))
    assert_blocked(decision, rule="procedencia")


def test_keys_that_are_not_a_front_are_not_checked_against_the_sources():
    data = con_hallazgos(datos_del_analista={"contenido": "volumen 100", "fuente": "analista"})
    assert con_fuentes().check_informe(data).allowed is True


def test_a_front_declared_uncovered_is_exempt_even_with_a_finding():
    from due_diligence.tests.test_rules_cobertura import declared, fail

    book = con_fuentes()
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias")
    data = informe_con(
        "no_habilitar",
        hallazgos={"noticias": hallazgo("diario_ficticio")},
        cobertura=declared("noticias"),
    )
    assert book.check_informe(data).allowed is True


def test_a_finding_of_a_front_that_never_responded_is_rejected_with_that_reason():
    book = observe_registro(CaseBook(), comercio())
    decision = book.check_informe(con_hallazgos(noticias=hallazgo(SRC_NOTICIAS)))
    assert_blocked(decision, rule="procedencia", hint="no hay respuesta")


def test_a_failed_front_that_was_not_declared_is_reported_by_coverage_before_provenance():
    from due_diligence.tests.test_rules_cobertura import fail

    book = con_fuentes()
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias")
    data = con_hallazgos(noticias=hallazgo(SRC_NOTICIAS))
    assert_blocked(book.check_informe(data), rule="cobertura")


@pytest.mark.parametrize(
    "hallazgos", [None, [], "texto", {"noticias": "texto"}, {"noticias": None}, {"registro": 5}]
)
def test_findings_of_another_shape_never_raise(hallazgos):
    decision = con_fuentes().check_informe(informe_con("no_habilitar", hallazgos=hallazgos))
    if isinstance(hallazgos, dict) and hallazgos:
        assert_blocked(decision, rule="procedencia")
    else:
        assert decision.allowed is True


def test_escalating_requires_the_same_provenance():
    book = con_fuentes()
    mala = escalamiento("CO-XX-0001", hallazgos={"noticias": hallazgo("diario_ficticio")})
    assert_blocked(book.check_escalar(mala), rule="procedencia", hint="noticias")
    buena = escalamiento("CO-XX-0001", hallazgos={"noticias": hallazgo(SRC_NOTICIAS)})
    assert book.check_escalar(buena).allowed is True


def test_a_report_without_front_findings_is_accepted_as_before():
    assert con_fuentes().check_informe(informe("no_habilitar")).allowed is True


def test_a_corrupt_responded_state_raises_so_the_hook_can_fail_closed():
    book = con_fuentes()
    book.responded = None  # estado corrupto
    with pytest.raises(Exception):  # noqa: B017 - el hook convierte cualquier excepción en denegación
        book.check_informe(con_hallazgos(noticias=hallazgo(SRC_NOTICIAS)))


def test_the_reasons_name_every_problem_found():
    sin_fecha = {"contenido": "x", "fuente": SRC_RIESGO}
    decision = con_fuentes().check_informe(
        con_hallazgos(noticias=hallazgo("diario_ficticio"), riesgo=sin_fecha)
    )
    assert_blocked(decision, rule="procedencia", hint="noticias")
    assert "riesgo" in decision.reason.lower()


# ------------------------------------------------------------- revisión del #5 (code-reviewer)


@pytest.mark.parametrize(
    "clave",
    [
        "registro mercantil",
        "registro-mercantil",
        "Registro Mercantil",
        "REGISTRO_MERCANTIL",
        "registro_mercantil_ficticio",
        "registro",
    ],
)
def test_a_finding_key_in_another_spelling_of_the_front_is_still_checked(clave):
    """Entrada del code-reviewer: `registro mercantil` esquivaba la procedencia."""
    falso = {"contenido": "x", "fuente": "diario_inventado"}
    decision = CaseBook().check_informe(informe_con("no_habilitar", hallazgos={clave: falso}))
    assert_blocked(decision, rule="procedencia")


@pytest.mark.parametrize(
    "clave, esperado",
    [
        ("registro mercantil", "registro"),
        ("listas-restrictivas", "listas"),
        ("Riesgo Categoría", "riesgo"),
        ("noticias_adversas", "noticias"),
        ("datos_del_analista", None),
        ("volumen_y_riesgo", None),
        ("", None),
    ],
)
def test_front_of_alias_reads_the_front_from_the_first_word_of_the_key(clave, esperado):
    from due_diligence.rules import front_of_alias

    assert front_of_alias(clave) == esperado


def test_a_coverage_key_in_another_spelling_declares_the_front():
    from due_diligence.tests.test_rules_cobertura import fail

    book = con_fuentes()
    book.start_request("Investiga CO-XX-0001")
    fail(book, "noticias")
    cobertura = {"Noticias": {"estado": "sin_cubrir", "motivo": "no disponible"}}
    assert book.check_informe(informe_con("no_habilitar", cobertura=cobertura)).allowed is True


@pytest.mark.parametrize("escrito", ["co-xx-0004", "Co-Xx-0004", " CO-XX-0004 "])
def test_a_candidate_id_in_another_case_is_still_unidentified(escrito):
    """Entrada del code-reviewer: el id en minúsculas esquivaba la regla de ambigüedad."""
    book = ambiguo()
    assert_blocked(book.check_informe(informe_con("no_habilitar", escrito)), rule="ambiguedad")
    assert_blocked(book.check_escalar(escalamiento(escrito)), rule="ambiguedad")


def test_an_identified_candidate_in_another_case_is_not_blocked():
    book = ambiguo()
    observe_registro(book, comercio("CO-XX-0004", "PE-0004"), consulta="CO-XX-0004")
    assert book.check_informe(informe_con("no_habilitar", "CO-XX-0004")).allowed is True
