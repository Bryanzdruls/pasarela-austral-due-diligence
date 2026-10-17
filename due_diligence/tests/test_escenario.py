"""El arnés de escenario se comporta como el SDK: hooks de producción y herramientas reales.

Ninguna prueba llama al modelo. Datos ficticios del servidor (`mcp_server/data/`).
"""

import json

import pytest

from due_diligence.tests.escenario import Escenario

REGISTRO = "consultar_registro_mercantil"
LISTAS = "consultar_listas_restrictivas"
NOTICIAS = "buscar_noticias"


@pytest.fixture
def crear(tmp_path, monkeypatch):
    def _crear(faults="", **kwargs):
        return Escenario(tmp_path, monkeypatch, faults=faults, **kwargs)

    return _crear


async def test_an_allowed_call_runs_the_real_server_tool_and_returns_its_envelope(crear):
    escenario = crear()
    r = await escenario.llamar(REGISTRO, {"consulta": "CO-LB-0002"}, agente="registro_mercantil")
    assert r.permitida is True and r.regla is None and r.motivo is None
    assert r.respuesta["ok"] is True
    assert r.respuesta["content"]["matches"][0]["id"] == "CO-LB-0002"
    assert r.respuesta["metadata"]["source"] == "registro_mercantil_ficticio"


async def test_a_call_rejected_by_rule_1_is_not_executed_and_names_the_rule(crear):
    escenario = crear()
    r = await escenario.llamar(
        LISTAS, {"tipo": "comercio", "referencia": "CO-TV-0001"}, agente="listas_restrictivas"
    )
    assert r.permitida is False and r.regla == "1"
    assert "registro mercantil" in r.motivo
    assert r.respuesta is None


async def test_the_role_isolation_of_production_rejects_another_fronts_tool(crear):
    escenario = crear()
    r = await escenario.llamar(NOTICIAS, {"consulta": "x"}, agente="registro_mercantil")
    assert r.permitida is False and r.respuesta is None
    assert r.regla == "aislamiento"


async def test_the_response_feeds_the_case_book_through_post_tool_use(crear):
    escenario = crear()
    listas = {"tipo": "comercio", "referencia": "CO-LB-0002"}
    assert (await escenario.llamar(LISTAS, listas, agente="listas_restrictivas")).permitida is False
    await escenario.llamar(REGISTRO, {"consulta": "CO-LB-0002"}, agente="registro_mercantil")
    assert (await escenario.llamar(LISTAS, listas, agente="listas_restrictivas")).permitida is True


async def test_the_arnes_uses_the_hooks_of_build_options_so_dropping_one_changes_the_outcome(crear):
    sin_reglas = crear(sin_hooks=("PreToolUse-reglas",))
    r = await sin_reglas.llamar(
        LISTAS, {"tipo": "comercio", "referencia": "CO-TV-0001"}, agente="listas_restrictivas"
    )
    assert r.permitida is True  # sin el hook de reglas, la regla 1 no se aplica


async def test_the_request_hook_runs_and_the_stop_hook_answers(crear):
    escenario = crear()
    await escenario.solicitud("Necesito el due diligence de Libros del Faro SAS")
    assert await escenario.parada() == {}


async def test_the_stop_hook_demands_escalation_once_after_a_list_match(crear):
    escenario = crear()
    await escenario.llamar(REGISTRO, {"consulta": "CO-DA-0003"}, agente="registro_mercantil")
    await escenario.llamar(
        LISTAS, {"tipo": "persona", "referencia": "PE-0003"}, agente="listas_restrictivas"
    )
    primera = await escenario.parada()
    assert primera["decision"] == "block"
    assert await escenario.parada(activo=True) == {}


async def test_saved_reports_and_escalations_are_read_from_the_temporary_directory(crear):
    escenario = crear()
    informe = {
        "comercio_id": "CO-LB-0002",
        "recomendacion": "no_habilitar",
        "hallazgos": {"datos_del_analista": {"contenido": "x", "fuente": "analista"}},
        "cobertura": {"x": 1},
    }
    r = await escenario.llamar("registrar_informe", informe)
    assert r.permitida is True and r.respuesta["content"]["informe_id"] == "INF-0001"
    guardados = escenario.registros("INF")
    assert [g["id"] for g in guardados] == ["INF-0001"]
    assert guardados[0]["recomendacion"] == "no_habilitar"
    assert escenario.registros("ESC") == []


async def test_faults_activate_the_server_injection_and_do_not_leak_to_other_scenarios(crear):
    con_falla = crear(faults="noticias")
    r = await con_falla.llamar(NOTICIAS, {"consulta": "x"}, agente="noticias")
    assert r.permitida is True
    assert r.respuesta["ok"] is False and r.respuesta["retryable"] is True
    sin_falla = crear()
    r = await sin_falla.llamar(NOTICIAS, {"consulta": "Libros del Faro"}, agente="noticias")
    assert r.respuesta["ok"] is True


async def test_each_scenario_has_its_own_state(crear):
    uno, dos = crear(), crear()
    await uno.llamar(REGISTRO, {"consulta": "CO-LB-0002"}, agente="registro_mercantil")
    listas = {"tipo": "comercio", "referencia": "CO-LB-0002"}
    assert (await uno.llamar(LISTAS, listas, agente="listas_restrictivas")).permitida is True
    assert (await dos.llamar(LISTAS, listas, agente="listas_restrictivas")).permitida is False


async def test_the_post_hook_receives_the_tool_response_as_json_text(crear):
    escenario = crear()
    await escenario.llamar(REGISTRO, {"consulta": "CO-LB-0002"}, agente="registro_mercantil")
    ultima = escenario.entradas_post[-1]
    assert isinstance(ultima["tool_response"], str)
    assert json.loads(ultima["tool_response"])["ok"] is True
    assert ultima["tool_name"] == "mcp__pasarela-fuentes__consultar_registro_mercantil"
    assert ultima["agent_type"] == "registro_mercantil"
