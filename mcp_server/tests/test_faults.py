import pytest

from mcp_server.tools import listas, noticias, registro, riesgo


def test_only_the_configured_source_fails(monkeypatch):
    monkeypatch.setenv("PASARELA_FAULTS", "noticias")
    r = noticias.buscar_noticias("Tienda Verde")
    assert r == {
        "ok": False,
        "source": "noticias_ficticias",
        "error_code": "source_unavailable",
        "retryable": True,
        "partial": {},
    }
    assert registro.consultar_registro_mercantil("CO-TV-0001")["ok"] is True
    assert listas.consultar_listas_restrictivas("persona", "PE-0003")["ok"] is True
    assert riesgo.consultar_riesgo_categoria("apuestas")["ok"] is True


def test_non_retryable_mode(monkeypatch):
    monkeypatch.setenv("PASARELA_FAULTS", "noticias:no_reintentable")
    assert noticias.buscar_noticias("Tienda Verde")["retryable"] is False


def test_each_source_can_fail(monkeypatch):
    monkeypatch.setenv("PASARELA_FAULTS", "registro, listas ,riesgo")
    assert registro.consultar_registro_mercantil("CO-TV-0001")["ok"] is False
    assert listas.consultar_listas_restrictivas("persona", "PE-0003")["ok"] is False
    assert riesgo.consultar_riesgo_categoria("apuestas")["ok"] is False
    assert noticias.buscar_noticias("Tienda Verde")["ok"] is True


def test_no_variable_means_no_faults(monkeypatch):
    monkeypatch.delenv("PASARELA_FAULTS", raising=False)
    assert noticias.buscar_noticias("Tienda Verde")["ok"] is True


def test_variable_is_read_on_every_call(monkeypatch):
    monkeypatch.delenv("PASARELA_FAULTS", raising=False)
    assert noticias.buscar_noticias("Tienda Verde")["ok"] is True
    monkeypatch.setenv("PASARELA_FAULTS", "noticias")
    assert noticias.buscar_noticias("Tienda Verde")["ok"] is False
    monkeypatch.delenv("PASARELA_FAULTS")
    assert noticias.buscar_noticias("Tienda Verde")["ok"] is True


@pytest.mark.parametrize("raw", ["", " , ,"])
def test_blank_value_has_no_faults(monkeypatch, raw):
    monkeypatch.setenv("PASARELA_FAULTS", raw)
    assert noticias.buscar_noticias("Tienda Verde")["ok"] is True


@pytest.mark.parametrize("raw", ["noticia", "noticias:otro", "registro,xyz"])
def test_misconfigured_faults_fail_loudly(monkeypatch, raw):
    monkeypatch.setenv("PASARELA_FAULTS", raw)
    with pytest.raises(ValueError, match="PASARELA_FAULTS"):
        noticias.buscar_noticias("Tienda Verde")
