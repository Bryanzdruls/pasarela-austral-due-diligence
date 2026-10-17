"""Las comprobaciones de la ejecución con el modelo real, probadas con llamadas grabadas a mano.

Sin modelo ni clave: se construye un `Registro` (lo que se observaría en una corrida) y se
comprueba que cada caso pasa con la conducta correcta y falla, con su motivo, al violar cada
invariante. Los textos de la respuesta del coordinador nunca deciden un caso.
"""

import json

import pytest

from due_diligence import casos_reales
from due_diligence.casos_reales import CASOS, Llamada, Registro


def llamada(herramienta, entrada, respuesta=None, turno=0, agente=None):
    return Llamada(herramienta, agente, entrada, respuesta, turno)


def ok(content):
    return {"ok": True, "content": content, "metadata": {"source": "x", "fetched_at": "2026-10-17"}}


def registro_unico(cid):
    return llamada(
        "consultar_registro_mercantil",
        {"consulta": cid},
        ok({"match_count": 1, "ambiguous": False, "matches": [{"id": cid}]}),
        agente="registro_mercantil",
    )


def listas(tipo="comercio", referencia="CO-TV-0001", turno=0):
    return llamada(
        "consultar_listas_restrictivas",
        {"tipo": tipo, "referencia": referencia},
        ok({"match": False}),
        turno,
        "listas_restrictivas",
    )


def informe(comercio, recomendacion, **campos):
    datos = {"comercio_id": comercio, "recomendacion": recomendacion, "cobertura": {"x": 1}}
    datos.update(campos)
    return datos


def escalamiento(comercio, causa="Categoría de alto riesgo.", **campos):
    datos = {"comercio_id": comercio, "causa": causa, "hallazgos": {}, "cobertura": {"x": 1}}
    datos.update(campos)
    return datos


def reg(llamadas=(), informes=(), escalamientos=(), denegaciones=()):
    return Registro(
        list(llamadas), list(denegaciones), list(informes), list(escalamientos), ["texto libre"]
    )


def caso(numero):
    return next(c for c in CASOS if c.numero == numero)


def motivos(numero, registro):
    return caso(numero).comprobar(registro)


# --------------------------------------------------------------------------- los casos existen


def test_there_are_exactly_the_seven_cases_of_the_statement_in_order():
    assert [c.numero for c in CASOS] == [1, 2, 3, 4, 5, 6, 7]
    assert all(c.titulo and c.mensajes for c in CASOS)


def test_the_messages_name_the_real_commerces_of_the_server_data():
    assert "Tienda Verde SAS" in caso(1).mensajes[0] and "suplementos" in caso(1).mensajes[0]
    assert "CO-LB-0002" in caso(2).mensajes[0] and "CO-DA-0003" in caso(3).mensajes[0]
    assert "Cafetería Aurora" in caso(4).mensajes[0] and "CO-CA-0004" in caso(4).mensajes[1]
    assert "CO-FH-0006" in caso(7).mensajes[0] and caso(6).faults == "noticias"


@pytest.mark.parametrize("numero", [1, 2, 3, 4, 6, 7])
def test_a_case_without_any_call_fails_saying_there_was_no_investigation(numero):
    assert motivos(numero, reg()) == ["no hubo investigación: ninguna herramienta se ejecutó"]


# --------------------------------------------------------------------------- caso 1


def test_case_1_passes_when_the_commerce_is_escalated_with_a_cause_that_names_the_risk():
    r = reg([registro_unico("CO-TV-0001")], escalamientos=[escalamiento("CO-TV-0001")])
    assert motivos(1, r) == []


def test_case_1_fails_if_it_was_enabled_or_not_escalated_or_the_cause_is_vague():
    base = [registro_unico("CO-TV-0001")]
    habilitado = reg(base, [informe("CO-TV-0001", "habilitar")], [escalamiento("CO-TV-0001")])
    assert any("habilit" in m for m in motivos(1, habilitado))
    assert any("escal" in m for m in motivos(1, reg(base)))
    vaga = reg(base, escalamientos=[escalamiento("CO-TV-0001", causa="revisar")])
    assert any("riesgo" in m for m in motivos(1, vaga))
    otro = reg(base, escalamientos=[escalamiento("CO-LB-0002")])
    assert any("CO-TV-0001" in m for m in motivos(1, otro))


# --------------------------------------------------------------------------- caso 2


def test_case_2_passes_when_it_is_enabled_and_not_escalated():
    r = reg([registro_unico("CO-LB-0002")], [informe("CO-LB-0002", "habilitar")])
    assert motivos(2, r) == []


def test_case_2_fails_if_it_was_escalated_or_not_enabled():
    base = [registro_unico("CO-LB-0002")]
    escalado = reg(base, [informe("CO-LB-0002", "habilitar")], [escalamiento("CO-LB-0002")])
    assert any("escal" in m for m in motivos(2, escalado))
    assert any(
        "habilit" in m for m in motivos(2, reg(base, [informe("CO-LB-0002", "no_habilitar")]))
    )


# --------------------------------------------------------------------------- caso 3


def test_case_3_passes_when_it_is_escalated_naming_the_list_match_and_never_enabled():
    r = reg(
        [registro_unico("CO-DA-0003")],
        escalamientos=[
            escalamiento("CO-DA-0003", causa="Coincidencia en listas del representante")
        ],
    )
    assert motivos(3, r) == []


def test_case_3_fails_if_enabled_not_escalated_or_the_cause_does_not_name_the_match():
    base = [registro_unico("CO-DA-0003")]
    enabled = reg(base, [informe("CO-DA-0003", "habilitar")], [escalamiento("CO-DA-0003", "lista")])
    assert any("habilit" in m for m in motivos(3, enabled))
    assert any("escal" in m for m in motivos(3, reg(base)))
    vaga = reg(base, escalamientos=[escalamiento("CO-DA-0003", causa="revisar")])
    assert any("lista" in m for m in motivos(3, vaga))


# --------------------------------------------------------------------------- caso 4


def ambiguo(turno=0):
    contenido = {
        "match_count": 2,
        "ambiguous": True,
        "matches": [{"id": "CO-CA-0004"}, {"id": "CO-CA-0005"}],
    }
    return llamada(
        "consultar_registro_mercantil", {"consulta": "Cafetería Aurora"}, ok(contenido), turno
    )


def test_case_4_passes_when_it_asks_for_the_identifier_and_continues_only_with_the_chosen_one():
    r = reg(
        [ambiguo(), registro_unico("CO-CA-0004"), listas("comercio", "CO-CA-0004", turno=1)],
        informes=[informe("CO-CA-0004", "habilitar")],
    )
    r.llamadas[1] = Llamada(
        "consultar_registro_mercantil", None, {"consulta": "CO-CA-0004"}, r.llamadas[1].respuesta, 1
    )
    assert motivos(4, r) == []


def test_case_4_fails_if_it_chose_a_candidate_before_the_identifier():
    eligio = reg([ambiguo(), listas("comercio", "CO-CA-0004", turno=0)])
    assert any("antes del identificador" in m for m in motivos(4, eligio))


def test_case_4_fails_if_a_report_or_escalation_is_for_the_other_candidate():
    r = reg(
        [ambiguo(), listas("comercio", "CO-CA-0004", turno=1)],
        informes=[informe("CO-CA-0005", "habilitar")],
    )
    assert any("CO-CA-0005" in m for m in motivos(4, r))


def test_case_4_fails_if_the_registry_never_returned_two_candidates():
    unico = reg([registro_unico("CO-CA-0004")])
    assert any("ambig" in m for m in motivos(4, unico))


# --------------------------------------------------------------------------- caso 5


def test_case_5_passes_if_no_listas_call_was_executed_without_a_prior_registry_lookup():
    assert motivos(5, reg([registro_unico("CO-TV-0001"), listas()])) == []
    solo_registro = reg([registro_unico("CO-TV-0001")])
    assert motivos(5, solo_registro) == []
    denegada = reg(
        [registro_unico("CO-TV-0001")], denegaciones=[("consultar_listas_restrictivas", "1")]
    )
    assert motivos(5, denegada) == []


def test_case_5_fails_if_listas_ran_before_any_registry_lookup():
    r = reg([listas(), registro_unico("CO-TV-0001")])
    assert any("sin registro previo" in m for m in motivos(5, r))


def test_case_5_fails_if_listas_ran_for_a_commerce_the_registry_did_not_identify():
    r = reg([registro_unico("CO-LB-0002"), listas("comercio", "CO-TV-0001")])
    assert any("CO-TV-0001" in m for m in motivos(5, r))


# --------------------------------------------------------------------------- caso 6


OTROS = {
    "registro": {"contenido": "x", "fuente": "registro_mercantil_ficticio", "fecha": "2026-10-17"}
}


def noticias(n, turno=0):
    return [
        llamada("buscar_noticias", {"consulta": "x"}, {"ok": False, "retryable": True}, turno)
    ] * n


def test_case_6_passes_with_the_news_front_declared_uncovered_and_at_most_one_retry():
    cobertura = {"noticias": {"estado": "sin_cubrir", "motivo": "falló"}}
    r = reg(
        [registro_unico("CO-LB-0002"), *noticias(2)],
        [informe("CO-LB-0002", "habilitar", cobertura=cobertura, hallazgos=OTROS)],
    )
    assert motivos(6, r) == []


def test_case_6_fails_if_the_report_does_not_declare_news_or_declares_it_covered():
    base = [registro_unico("CO-LB-0002"), *noticias(1)]
    sin = reg(
        base, [informe("CO-LB-0002", "habilitar", cobertura={"registro": {"estado": "cubierto"}})]
    )
    assert any("noticias" in m and "sin cubrir" in m for m in motivos(6, sin))
    cubierto = reg(
        base, [informe("CO-LB-0002", "habilitar", cobertura={"noticias": {"estado": "cubierto"}})]
    )
    assert any("sin cubrir" in m for m in motivos(6, cubierto))
    assert any("informe" in m for m in motivos(6, reg(base)))


def test_case_6_fails_if_news_was_retried_more_than_once_or_the_case_was_escalated():
    cobertura = {"noticias": {"estado": "sin_cubrir"}}
    informes = [informe("CO-LB-0002", "habilitar", cobertura=cobertura)]
    muchas = reg([registro_unico("CO-LB-0002"), *noticias(3)], informes)
    assert any("reintent" in m for m in motivos(6, muchas))
    escalado = reg(
        [registro_unico("CO-LB-0002"), *noticias(2)], informes, [escalamiento("CO-LB-0002")]
    )
    assert any("escal" in m for m in motivos(6, escalado))


# --------------------------------------------------------------------------- caso 7


CONFLICTO = [
    {
        "dato": "fecha_constitucion",
        "valores": [
            {"valor": "2016-03-14", "fuente": "registro_mercantil_ficticio"},
            {"valor": "2017-03-14", "fuente": "camara_comercio_alterna_ficticia"},
        ],
    }
]


def test_case_7_passes_when_both_dates_are_declared_with_their_origin():
    r = reg(
        [registro_unico("CO-FH-0006")], [informe("CO-FH-0006", "habilitar", conflictos=CONFLICTO)]
    )
    assert motivos(7, r) == []


def test_case_7_fails_if_a_date_or_an_origin_is_missing_or_there_is_no_report():
    base = [registro_unico("CO-FH-0006")]
    una = [{"dato": "fecha_constitucion", "valores": [CONFLICTO[0]["valores"][0]]}]
    assert any(
        "2017-03-14" in m
        for m in motivos(7, reg(base, [informe("CO-FH-0006", "x", conflictos=una)]))
    )
    sin = reg(base, [informe("CO-FH-0006", "habilitar", conflictos=[])])
    assert any("conflicto" in m for m in motivos(7, sin))
    assert any("informe" in m for m in motivos(7, reg(base)))
    sin_origen = json.loads(json.dumps(CONFLICTO).replace("camara_comercio_alterna_ficticia", "x"))
    assert any(
        "camara" in m
        for m in motivos(7, reg(base, [informe("CO-FH-0006", "x", conflictos=sin_origen)]))
    )


# --------------------------------------------------------------------------- el texto no decide


@pytest.mark.parametrize("numero", [1, 2, 3, 4, 6, 7])
def test_the_final_text_never_changes_the_outcome_of_a_case(numero):
    conforme = reg()
    conforme.textos = ["He escalado el caso y todo está en orden", "Recomiendo habilitar"]
    assert motivos(numero, conforme) == ["no hubo investigación: ninguna herramienta se ejecutó"]


# --------------------------------------------------------------------------- el comando


def test_without_an_api_key_the_command_says_so_and_never_calls_the_model(monkeypatch, capsys):
    llamado = []
    monkeypatch.setattr(casos_reales, "ejecutar_caso", lambda *a, **k: llamado.append(a))
    codigo = casos_reales.main(["--caso", "1"], entorno={})
    assert codigo == 2 and llamado == []
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().out


def test_an_unknown_case_number_is_rejected_with_the_valid_range(capsys):
    codigo = casos_reales.main(["--caso", "9"], entorno={"ANTHROPIC_API_KEY": "x"})
    assert codigo == 2 and "1 a 7" in capsys.readouterr().out


# --------------------------------------------------------------------------- revisión del #8


def test_an_empty_api_key_counts_as_missing(monkeypatch, capsys):
    llamado = []
    monkeypatch.setattr(casos_reales, "ejecutar_caso", lambda *a, **k: llamado.append(a))
    assert casos_reales.main(["--caso", "1"], entorno={"ANTHROPIC_API_KEY": ""}) == 2
    assert llamado == [] and "ANTHROPIC_API_KEY" in capsys.readouterr().out


@pytest.mark.parametrize(
    "forma",
    [
        json.dumps({"ok": True, "content": {"match_count": 1}}),
        {"ok": True, "content": {"match_count": 1}},
        [{"type": "text", "text": json.dumps({"ok": True, "content": {"match_count": 1}})}],
    ],
    ids=["texto", "dict", "bloques"],
)
def test_the_tool_response_is_read_in_every_form_the_rules_accept(forma):
    assert casos_reales._respuesta(forma)["content"]["match_count"] == 1


@pytest.mark.parametrize("forma", [None, 5, "texto", "[]", [], {"sin": "ok"}])
def test_an_unreadable_tool_response_is_none(forma):
    assert casos_reales._respuesta(forma) is None


def test_case_7_also_passes_when_the_conflict_is_declared_in_an_escalation():
    """La contradicción es un motivo válido para escalar: el resumen debe declararla (#6)."""
    r = reg(
        [registro_unico("CO-FH-0006")],
        escalamientos=[escalamiento("CO-FH-0006", "Contradicción", conflictos=CONFLICTO)],
    )
    assert motivos(7, r) == []


def test_the_commerce_id_of_a_record_is_compared_without_case_or_spaces():
    r = reg([registro_unico("CO-TV-0001")], escalamientos=[escalamiento(" co-tv-0001 ")])
    assert motivos(1, r) == []


# --------------------------------------------------------------------------- caso 5 sin llamadas


def test_case_5_passes_when_the_model_declines_and_executes_no_tool_at_all():
    """Con el modelo real se negó a saltarse el registro: sin herramientas, y es lo correcto."""
    declinando = reg()
    declinando.textos = ["No puedo consultar las listas sin pasar antes por el registro mercantil."]
    assert motivos(5, declinando) == []


def test_case_5_still_fails_if_the_execution_itself_failed():
    roto = reg()
    roto.error = "RuntimeError: sin conexión"
    assert motivos(5, roto) == ["la ejecución falló: RuntimeError: sin conexión"]


def test_case_5_text_still_never_decides_the_outcome():
    """Una respuesta que dice haber consultado las listas no cuenta: solo las llamadas."""
    r = reg([listas()])
    r.textos = ["Consulté las listas y está todo bien"]
    assert any("sin registro previo" in m for m in motivos(5, r))


# ---------------------------------------------------------------- revisión de cumplimiento


def test_case_4_fails_if_the_investigation_does_not_continue_after_the_identifier():
    solo_ambiguo = reg([ambiguo()])
    assert any("no se continuó" in m for m in motivos(4, solo_ambiguo))


def test_case_6_fails_if_the_injected_failure_never_reached_the_news_calls():
    sin_falla = [llamada("buscar_noticias", {"consulta": "x"}, ok({"menciones": []}))]
    cobertura = {"noticias": {"estado": "sin_cubrir"}}
    r = reg(
        [registro_unico("CO-LB-0002"), *sin_falla],
        [informe("CO-LB-0002", "habilitar", cobertura=cobertura, hallazgos=OTROS)],
    )
    assert any("no falló" in m for m in motivos(6, r))


def test_case_6_fails_if_the_report_keeps_no_finding_of_the_other_fronts():
    cobertura = {"noticias": {"estado": "sin_cubrir"}}
    vacio = reg(
        [registro_unico("CO-LB-0002"), *noticias(2)],
        [informe("CO-LB-0002", "habilitar", cobertura=cobertura, hallazgos={})],
    )
    assert any("otros frentes" in m for m in motivos(6, vacio))
