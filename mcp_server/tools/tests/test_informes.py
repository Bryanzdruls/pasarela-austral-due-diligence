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


def test_findings_without_source_are_rejected(runtime):
    for hallazgos in ({"x": "algo"}, {"x": {"dato": 1}}, {"x": {"fuente": "  "}}):
        r = informes.escalar_a_cumplimiento(**_escalamiento(hallazgos=hallazgos))
        assert r["ok"] is False and r["partial"]["hallazgos_sin_fuente"] == ["x"]
        r = informes.registrar_informe(**_informe(hallazgos=hallazgos))
        assert r["ok"] is False and r["partial"]["hallazgos_sin_fuente"] == ["x"]
    assert not list(runtime.glob("*.json"))


def test_whitespace_only_text_counts_as_missing():
    r = informes.escalar_a_cumplimiento(**_escalamiento(causa="   "))
    assert r["partial"]["campos_faltantes"] == ["causa"]


def test_text_fields_are_stripped_before_saving(runtime):
    informes.escalar_a_cumplimiento(**_escalamiento(causa="  alto riesgo  "))
    saved = json.loads((runtime / "ESC-0001.json").read_text(encoding="utf-8"))
    assert saved["causa"] == "alto riesgo"


def test_report_with_no_arguments_returns_structured_error():
    r = informes.registrar_informe()
    assert r["ok"] is False and r["error_code"] == "invalid_input"
    assert r["partial"]["campos_faltantes"] == [
        "comercio_id",
        "recomendacion",
        "hallazgos",
        "cobertura",
    ]


def test_the_escalation_stores_the_conflicts_it_was_given(runtime):
    conflictos = [{"dato": "fecha_constitucion", "valores": [{"valor": "a", "fuente": "x"}]}]
    r = informes.escalar_a_cumplimiento(**_escalamiento(conflictos=conflictos))
    assert r["ok"] is True
    saved = json.loads((runtime / "ESC-0001.json").read_text(encoding="utf-8"))
    assert saved["conflictos"] == conflictos


def test_the_escalation_without_conflicts_stores_an_empty_list(runtime):
    informes.escalar_a_cumplimiento(**_escalamiento())
    saved = json.loads((runtime / "ESC-0001.json").read_text(encoding="utf-8"))
    assert saved["conflictos"] == []
