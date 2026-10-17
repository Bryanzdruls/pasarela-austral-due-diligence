"""Los siete casos de prueba obligatorios del enunciado, de extremo a extremo y sin modelo.

Cada prueba recorre los datos ficticios reales del servidor (`mcp_server/data/`), las herramientas
reales del servidor y los hooks de producción (`build_options`), y comprueba lo que el enunciado
exige: qué se permite, qué se rechaza y con qué regla, qué queda registrado y si la respuesta puede
cerrarse. Lo único simulado es qué herramienta llama el modelo (el guion de cada caso). La misma
lista de casos se ejecuta con el modelo real con `python scripts/run_casos.py`
(ver `docs/CASOS.md`).
"""

import pytest

from due_diligence.tests.escenario import Escenario

REGISTRO = "consultar_registro_mercantil"
LISTAS = "consultar_listas_restrictivas"
NOTICIAS = "buscar_noticias"
RIESGO = "consultar_riesgo_categoria"
INFORME = "registrar_informe"
ESCALAR = "escalar_a_cumplimiento"

REG = "registro_mercantil"
LIS = "listas_restrictivas"
NOT = "noticias"
RIE = "riesgo_categoria"


@pytest.fixture
def crear(tmp_path, monkeypatch):
    def _crear(faults=""):
        return Escenario(tmp_path, monkeypatch, faults=faults)

    return _crear


# --------------------------------------------------------------------------- ayudas del guion


async def consultar_frentes(escenario, comercio, nombre, representante, categoria):
    """Lo que hace el coordinador con los cuatro frentes de un comercio; devuelve las respuestas."""
    registro = await escenario.llamar(REGISTRO, {"consulta": nombre}, agente=REG)
    assert registro.permitida and registro.respuesta["content"]["match_count"] == 1
    assert registro.respuesta["content"]["matches"][0]["id"] == comercio
    respuestas = {"registro": registro.respuesta}
    pedidas = (
        ("riesgo", RIESGO, {"categoria": categoria}, RIE),
        ("listas", LISTAS, {"tipo": "comercio", "referencia": comercio}, LIS),
        ("listas_persona", LISTAS, {"tipo": "persona", "referencia": representante}, LIS),
        ("noticias", NOTICIAS, {"consulta": f"{nombre} {comercio}"}, NOT),
    )
    for clave, herramienta, entrada, agente in pedidas:
        r = await escenario.llamar(herramienta, entrada, agente=agente)
        assert r.permitida, (clave, r.regla, r.motivo)
        respuestas[clave] = r.respuesta
    return respuestas


def hallazgo(respuesta, contenido="resultado de la consulta"):
    """Un hallazgo con la fuente y la fecha que devolvió el servidor."""
    metadatos = respuesta["metadata"]
    return {"contenido": contenido, "fuente": metadatos["source"], "fecha": metadatos["fetched_at"]}


def hallazgos(respuestas, *frentes):
    return {f: hallazgo(respuestas[f]) for f in frentes}


COBERTURA_COMPLETA = {
    f: {"estado": "cubierto"} for f in ("registro", "listas", "noticias", "riesgo")
}
CUATRO = ("registro", "listas", "noticias", "riesgo")


# --------------------------------------------------------------------------- caso 1


async def test_case_1_a_high_risk_commerce_goes_to_a_compliance_officer(crear):
    """Tienda Verde SAS (suplementos dietarios): no se habilita; se escala con resumen completo."""
    e = crear()
    await e.solicitud(
        "Necesito el due diligence de Tienda Verde SAS. Quieren procesar ventas en línea de "
        "suplementos dietarios. ¿Lo habilitamos?"
    )
    r = await consultar_frentes(
        e, "CO-TV-0001", "Tienda Verde SAS", "PE-0001", "suplementos dietarios"
    )
    assert r["riesgo"]["content"]["riesgo"] == "alto"

    # habilitar es rechazado por la regla 3: un alto riesgo nunca se habilita automáticamente
    informe = {
        "comercio_id": "CO-TV-0001",
        "recomendacion": "habilitar",
        "hallazgos": hallazgos(r, *CUATRO),
        "cobertura": COBERTURA_COMPLETA,
    }
    rechazado = await e.llamar(INFORME, informe)
    assert (rechazado.permitida, rechazado.regla) == (False, "3")
    assert "oficial de cumplimiento" in rechazado.motivo
    assert e.registros("INF") == []

    # el sistema no deja cerrar la respuesta sin escalar (una sola vez)
    pendiente = await e.parada()
    assert pendiente["decision"] == "block" and "CO-TV-0001" in pendiente["reason"]

    # recomendar escalar y escalar se permiten y quedan registrados con un resumen completo
    escalar = {**informe, "recomendacion": "escalar_a_cumplimiento"}
    assert (await e.llamar(INFORME, escalar)).permitida
    resumen = {
        "comercio_id": "CO-TV-0001",
        "hallazgos": hallazgos(r, "registro", "riesgo", "listas", "noticias"),
        "cobertura": COBERTURA_COMPLETA,
        "causa": "Categoría de alto riesgo: suplementos dietarios; hay noticias del comercio.",
        "accion_recomendada": "No habilitar; revisión manual de la categoría de alto riesgo.",
    }
    escalado = await e.llamar(ESCALAR, resumen)
    assert escalado.permitida and escalado.respuesta["content"]["escalamiento_id"] == "ESC-0001"
    guardado = e.registros("ESC")[0]
    assert guardado["comercio_id"] == "CO-TV-0001" and "alto riesgo" in guardado["causa"]
    assert set(guardado["hallazgos"]) == {"registro", "riesgo", "listas", "noticias"}
    assert all(h["fuente"] and h["fecha"] for h in guardado["hallazgos"].values())
    assert await e.parada() == {}


# --------------------------------------------------------------------------- caso 2


async def test_case_2_a_low_risk_commerce_without_findings_is_enabled(crear):
    """Libros del Faro SAS (riesgo bajo, sin hallazgos): se habilita y no se escala."""
    e = crear()
    await e.solicitud(
        "Necesito el due diligence de Libros del Faro SAS. Si todo está bien, habilítalo."
    )
    r = await consultar_frentes(e, "CO-LB-0002", "Libros del Faro SAS", "PE-0002", "libreria")
    assert r["riesgo"]["content"]["riesgo"] == "bajo"
    assert (
        r["listas"]["content"]["match"] is False
        and r["listas_persona"]["content"]["match"] is False
    )

    # no hay motivo para escalar: ni la herramienta ni la recomendación
    informe_escalar = {
        "comercio_id": "CO-LB-0002",
        "recomendacion": "escalar_a_cumplimiento",
        "hallazgos": hallazgos(r, *CUATRO),
        "cobertura": COBERTURA_COMPLETA,
    }
    rechazado = await e.llamar(INFORME, informe_escalar)
    assert (rechazado.permitida, rechazado.regla) == (False, "escalamiento")
    assert "habilitar" in rechazado.motivo
    resumen = {
        "comercio_id": "CO-LB-0002",
        "hallazgos": hallazgos(r, "registro"),
        "cobertura": COBERTURA_COMPLETA,
        "causa": "revisión preventiva",
        "accion_recomendada": "revisar",
    }
    assert (await e.llamar(ESCALAR, resumen)).regla == "escalamiento"
    assert e.registros("ESC") == []

    # habilitar se acepta y queda registrado con fuente y fecha por hallazgo
    informe = {**informe_escalar, "recomendacion": "habilitar"}
    aceptado = await e.llamar(INFORME, informe)
    assert aceptado.permitida and aceptado.respuesta["content"]["informe_id"] == "INF-0001"
    guardado = e.registros("INF")[0]
    assert guardado["recomendacion"] == "habilitar" and guardado["conflictos"] == []
    assert all(h["fuente"] and h["fecha"] for h in guardado["hallazgos"].values())
    assert await e.parada() == {}


# --------------------------------------------------------------------------- caso 3


async def test_case_3_a_legal_representative_with_a_list_match_blocks_enabling_and_escalates(crear):
    """Distribuidora Andina Ficticia SAS: su representante (PE-0003) está en listas restrictivas."""
    e = crear()
    await e.solicitud("Necesito el due diligence de Distribuidora Andina Ficticia SAS.")
    r = await consultar_frentes(
        e, "CO-DA-0003", "Distribuidora Andina Ficticia SAS", "PE-0003", "ferreteria"
    )
    assert r["listas"]["content"]["match"] is False
    assert r["listas_persona"]["content"]["match"] is True

    # la coincidencia del representante impide habilitar (regla 2) y obliga a escalar
    informe = {
        "comercio_id": "CO-DA-0003",
        "recomendacion": "habilitar",
        "hallazgos": hallazgos(r, "registro", "listas", "riesgo"),
        "cobertura": COBERTURA_COMPLETA,
    }
    rechazado = await e.llamar(INFORME, informe)
    assert (rechazado.permitida, rechazado.regla) == (False, "2")
    assert "representante" in rechazado.motivo
    assert (await e.parada())["decision"] == "block"

    # un resumen sin el hallazgo de listas no le sirve al oficial; con él se acepta
    base = {
        "comercio_id": "CO-DA-0003",
        "cobertura": COBERTURA_COMPLETA,
        "causa": "Coincidencia en listas restrictivas del representante legal PE-0003.",
        "accion_recomendada": "No habilitar; confirmar que no es un homónimo.",
    }
    sin_listas = await e.llamar(ESCALAR, {**base, "hallazgos": hallazgos(r, "registro")})
    assert (sin_listas.permitida, sin_listas.regla) == (False, "handoff_hallazgos")
    completo = {
        **base,
        "hallazgos": {**hallazgos(r, "registro"), "listas": hallazgo(r["listas_persona"])},
    }
    escalado = await e.llamar(ESCALAR, completo)
    assert escalado.permitida
    guardado = e.registros("ESC")[0]
    assert guardado["comercio_id"] == "CO-DA-0003" and "listas" in guardado["hallazgos"]
    assert "PE-0003" in guardado["causa"]
    assert await e.parada() == {}


# --------------------------------------------------------------------------- caso 4


async def test_case_4_two_commerces_with_almost_identical_names_ask_for_the_identifier(crear):
    """Cafetería Aurora: el registro devuelve dos comercios; no se elige ninguno."""
    e = crear()
    await e.solicitud("Necesito el due diligence de Cafetería Aurora.")
    r = await e.llamar(REGISTRO, {"consulta": "Cafetería Aurora"}, agente=REG)
    contenido = r.respuesta["content"]
    assert contenido["ambiguous"] is True and contenido["match_count"] == 2
    candidatos = {m["id"] for m in contenido["matches"]}
    assert candidatos == {"CO-CA-0004", "CO-CA-0005"}

    # ninguno está identificado: ni listas, ni informe, ni escalamiento a nombre de un candidato
    for candidato in sorted(candidatos):
        listas = await e.llamar(LISTAS, {"tipo": "comercio", "referencia": candidato}, agente=LIS)
        assert (listas.permitida, listas.regla) == (False, "1")
    informe = {
        "comercio_id": "CO-CA-0004",
        "recomendacion": "no_habilitar",
        "hallazgos": {"datos_del_analista": {"contenido": "nombre dado", "fuente": "analista"}},
        "cobertura": {"x": 1},
    }
    por_informe = await e.llamar(INFORME, informe)
    assert (por_informe.permitida, por_informe.regla) == (False, "ambiguedad")
    assert "identificador" in por_informe.motivo
    resumen = {
        "comercio_id": "CO-CA-0005",
        "hallazgos": {},
        "cobertura": {"x": 1},
        "causa": "revisar",
        "accion_recomendada": "revisar",
    }
    assert (await e.llamar(ESCALAR, resumen)).regla == "ambiguedad"

    # el analista da el identificador: el registro lo identifica y la investigación sigue con él
    await e.solicitud("CO-CA-0004")
    elegido = await e.llamar(REGISTRO, {"consulta": "CO-CA-0004"}, agente=REG)
    assert elegido.respuesta["content"]["match_count"] == 1
    permitida = await e.llamar(LISTAS, {"tipo": "comercio", "referencia": "CO-CA-0004"}, agente=LIS)
    assert permitida.permitida
    assert (await e.llamar(INFORME, informe)).permitida
    otro = await e.llamar(INFORME, {**informe, "comercio_id": "CO-CA-0005"})
    assert (otro.permitida, otro.regla) == (False, "ambiguedad")
    assert [i["comercio_id"] for i in e.registros("INF")] == ["CO-CA-0004"]


# --------------------------------------------------------------------------- caso 5


async def test_case_5_listas_without_a_prior_registry_lookup_is_blocked(crear):
    """Consulta directa a listas, sin pasar por el registro: bloqueada y no llega al servidor."""
    e = crear()
    r = await e.llamar(LISTAS, {"tipo": "comercio", "referencia": "CO-TV-0001"}, agente=LIS)
    assert (r.permitida, r.regla) == (False, "1")
    assert "identificado de forma unívoca" in r.motivo
    assert r.respuesta is None and e.entradas_post == []


async def test_case_5_listas_after_an_ambiguous_registry_result_is_blocked(crear):
    e = crear()
    await e.llamar(REGISTRO, {"consulta": "Cafetería Aurora"}, agente=REG)
    for candidato in ("CO-CA-0004", "CO-CA-0005"):
        r = await e.llamar(LISTAS, {"tipo": "comercio", "referencia": candidato}, agente=LIS)
        assert (r.permitida, r.regla) == (False, "1")
    assert [p["tool_name"] for p in e.entradas_post] == [PREFIX_REGISTRO]


PREFIX_REGISTRO = "mcp__pasarela-fuentes__consultar_registro_mercantil"


async def test_case_5_listas_of_a_person_who_is_not_the_representative_is_blocked(crear):
    e = crear()
    await e.llamar(REGISTRO, {"consulta": "CO-LB-0002"}, agente=REG)  # representante: PE-0002
    ajena = await e.llamar(LISTAS, {"tipo": "persona", "referencia": "PE-0001"}, agente=LIS)
    assert (ajena.permitida, ajena.regla) == (False, "1")
    # con el comercio identificado, su comercio y su representante sí se consultan
    assert (
        await e.llamar(LISTAS, {"tipo": "comercio", "referencia": "CO-LB-0002"}, agente=LIS)
    ).permitida
    propia = await e.llamar(LISTAS, {"tipo": "persona", "referencia": "PE-0002"}, agente=LIS)
    assert propia.permitida and propia.respuesta["content"]["match"] is False


# --------------------------------------------------------------------------- caso 6


async def _frentes_sin_noticias(e):
    r = {}
    r["registro"] = (
        await e.llamar(REGISTRO, {"consulta": "Libros del Faro SAS"}, agente=REG)
    ).respuesta
    r["riesgo"] = (await e.llamar(RIESGO, {"categoria": "libreria"}, agente=RIE)).respuesta
    listas = {"tipo": "comercio", "referencia": "CO-LB-0002"}
    r["listas"] = (await e.llamar(LISTAS, listas, agente=LIS)).respuesta
    persona = {"tipo": "persona", "referencia": "PE-0002"}
    await e.llamar(LISTAS, persona, agente=LIS)
    return r


async def test_case_6_a_news_failure_produces_a_report_that_declares_the_incomplete_coverage(crear):
    """Falla de noticias: el informe declara `noticias` sin cubrir, sin inventar nada."""
    e = crear(faults="noticias")
    await e.solicitud("Necesito el due diligence de Libros del Faro SAS.")
    r = await _frentes_sin_noticias(e)
    consulta = {"consulta": "Libros del Faro SAS"}

    # la falla llega como error estructurado y reintentable; se reintenta una vez y no más
    primero = await e.llamar(NOTICIAS, consulta, agente=NOT)
    assert primero.respuesta["ok"] is False and primero.respuesta["retryable"] is True
    assert (await e.llamar(NOTICIAS, consulta, agente=NOT)).permitida
    tercero = await e.llamar(NOTICIAS, consulta, agente=NOT)
    assert (tercero.permitida, tercero.regla) == (False, "reintento")

    # el informe que no declara la falla no se registra; el que la declara se acepta
    informe = {
        "comercio_id": "CO-LB-0002",
        "recomendacion": "habilitar",
        "hallazgos": hallazgos(r, "registro", "listas", "riesgo"),
        "cobertura": {"registro": {"estado": "cubierto"}, "listas": {"estado": "cubierto"}},
    }
    omite = await e.llamar(INFORME, informe)
    assert (omite.permitida, omite.regla) == (False, "cobertura")
    assert "noticias" in omite.motivo
    declarada = {**informe["cobertura"], "noticias": {"estado": "sin_cubrir", "motivo": "falló"}}
    aceptado = await e.llamar(INFORME, {**informe, "cobertura": declarada})
    assert aceptado.permitida
    guardado = e.registros("INF")[0]
    assert guardado["cobertura"]["noticias"]["estado"] == "sin_cubrir"
    assert set(guardado["hallazgos"]) == {"registro", "listas", "riesgo"}  # nada inventado

    # una cobertura incompleta, sola, no es un hallazgo: no se escala
    resumen = {
        "comercio_id": "CO-LB-0002",
        "hallazgos": hallazgos(r, "registro"),
        "cobertura": declarada,
        "causa": "revisión por falta de noticias",
        "accion_recomendada": "revisar",
    }
    assert (await e.llamar(ESCALAR, resumen)).regla == "escalamiento"
    assert await e.parada() == {}


async def test_case_6_a_non_retryable_news_failure_is_not_retried(crear):
    e = crear(faults="noticias:no_reintentable")
    consulta = {"consulta": "Libros del Faro SAS"}
    primero = await e.llamar(NOTICIAS, consulta, agente=NOT)
    assert primero.respuesta["ok"] is False and primero.respuesta["retryable"] is False
    segundo = await e.llamar(NOTICIAS, consulta, agente=NOT)
    assert (segundo.permitida, segundo.regla) == (False, "reintento")
    assert "no es reintentable" in segundo.motivo


# --------------------------------------------------------------------------- caso 7


async def test_case_7_two_sources_with_different_incorporation_dates_are_shown_together(crear):
    """Ferretería Horizonte SAS: el registro y la cámara alterna difieren; no se elige una fecha."""
    e = crear()
    await e.solicitud("Necesito el due diligence de Ferretería Horizonte SAS.")
    r = await consultar_frentes(
        e, "CO-FH-0006", "Ferretería Horizonte SAS", "PE-0006", "ferreteria"
    )
    coincidencia = r["registro"]["content"]["matches"][0]
    assert coincidencia["conflicts"] == ["fecha_constitucion"]
    fechas = {f["source"]: f["fecha_constitucion"] for f in coincidencia["fuentes_registro"]}
    assert fechas == {
        "registro_mercantil_ficticio": "2016-03-14",
        "camara_comercio_alterna_ficticia": "2017-03-14",
    }

    informe = {
        "comercio_id": "CO-FH-0006",
        "recomendacion": "no_habilitar",
        "hallazgos": hallazgos(r, *CUATRO),
        "cobertura": COBERTURA_COMPLETA,
    }
    # un informe que presenta una sola fecha, o no declara el conflicto, no se registra
    una_sola = await e.llamar(INFORME, informe)
    assert (una_sola.permitida, una_sola.regla) == (False, "conflicto")
    assert "fecha_constitucion" in una_sola.motivo
    incompleto = {
        "dato": "fecha_constitucion",
        "valores": [{"valor": "2016-03-14", "fuente": "registro_mercantil_ficticio"}],
    }
    assert (await e.llamar(INFORME, {**informe, "conflictos": [incompleto]})).regla == "conflicto"

    # declarando ambas fechas con su origen, el informe se registra
    ambas = {
        "dato": "fecha_constitucion",
        "valores": [
            {"valor": "2016-03-14", "fuente": "registro_mercantil_ficticio"},
            {"valor": "2017-03-14", "fuente": "camara_comercio_alterna_ficticia"},
        ],
    }
    aceptado = await e.llamar(INFORME, {**informe, "conflictos": [ambas]})
    assert aceptado.permitida
    guardado = e.registros("INF")[0]
    assert guardado["conflictos"] == [ambas]
    assert await e.parada() == {}
