import json

import pytest

from mcp_server.tools import informes


@pytest.fixture(autouse=True)
def runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("PASARELA_RUNTIME_DIR", str(tmp_path))
    return tmp_path


def _informe(**over):
    base = {
        "comercio_id": "CO-LB-0002",
        "recomendacion": "habilitar",
        "hallazgos": {"registro": {"dato": "activo", "fuente": "registro_mercantil_ficticio"}},
        "cobertura": {"cubiertos": ["registro"], "sin_cubrir": []},
    }
    return {**base, **over}


def test_report_is_stored_as_given(runtime):
    r = informes.registrar_informe(**_informe())
    assert r["ok"] is True and r["content"]["informe_id"] == "INF-0001"
    saved = json.loads((runtime / "INF-0001.json").read_text(encoding="utf-8"))
    assert saved["comercio_id"] == "CO-LB-0002" and saved["recomendacion"] == "habilitar"


def test_two_reports_for_same_commerce_get_distinct_ids():
    a = informes.registrar_informe(**_informe())["content"]["informe_id"]
    b = informes.registrar_informe(**_informe())["content"]["informe_id"]
    assert a != b


def test_server_does_not_decide_the_recommendation():
    # FR-013: aunque el representante esté en listas, el servidor solo guarda.
    r = informes.registrar_informe(**_informe(comercio_id="CO-DA-0003", recomendacion="habilitar"))
    assert r["ok"] is True


def test_report_missing_fields_is_rejected():
    r = informes.registrar_informe(**_informe(recomendacion=""))
    assert r["ok"] is False and r["partial"]["campos_faltantes"] == ["recomendacion"]


def _escalamiento(**over):
    base = {
        "comercio_id": "CO-TV-0001",
        "hallazgos": {"categoria": {"riesgo": "alto", "fuente": "catalogo_riesgo_ficticio"}},
        "cobertura": {"cubiertos": ["registro", "riesgo"], "sin_cubrir": []},
        "causa": "categoría de alto riesgo",
        "accion_recomendada": "revisión manual por oficial de cumplimiento",
    }
    return {**base, **over}


def test_complete_escalation_is_stored(runtime):
    r = informes.escalar_a_cumplimiento(**_escalamiento())
    assert r["content"]["escalamiento_id"] == "ESC-0001"
    assert (runtime / "ESC-0001.json").exists()


@pytest.mark.parametrize("campo", ["causa", "accion_recomendada", "hallazgos", "cobertura"])
def test_incomplete_escalation_lists_missing_fields(campo, runtime):
    r = informes.escalar_a_cumplimiento(**_escalamiento(**{campo: None}))
    assert r["ok"] is False and r["error_code"] == "invalid_input"
    assert r["partial"]["campos_faltantes"] == [campo]
    assert not list(runtime.glob("ESC-*.json"))
