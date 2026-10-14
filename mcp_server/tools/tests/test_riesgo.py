import pytest

from mcp_server.tools import riesgo


@pytest.mark.parametrize(
    "categoria",
    ["apuestas", "criptoactivos", "suplementos dietarios", "venta de medicamentos"],
)
def test_high_risk_categories(categoria):
    r = riesgo.consultar_riesgo_categoria(categoria)
    assert r["content"]["riesgo"] == "alto"
    assert r["metadata"]["source"] == "catalogo_riesgo_ficticio"


def test_low_risk_and_accent_insensitive():
    assert riesgo.consultar_riesgo_categoria("Librería")["content"]["riesgo"] == "bajo"


def test_unknown_category_is_unclassified():
    assert riesgo.consultar_riesgo_categoria("minería")["content"]["riesgo"] == "sin_clasificar"


def test_blank_is_invalid():
    assert riesgo.consultar_riesgo_categoria("")["error_code"] == "invalid_input"


def test_description_lists_high_risk_and_warns_on_unclassified():
    d = riesgo.DESCRIPTION
    for c in ("apuestas", "criptoactivos", "suplementos dietarios", "venta de medicamentos"):
        assert c in d
    assert "sin_clasificar" in d and "no asumas" in d
