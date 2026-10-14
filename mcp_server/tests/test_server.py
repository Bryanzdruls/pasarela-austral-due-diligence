import asyncio

from mcp_server.server import server

EXPECTED = {
    "consultar_registro_mercantil",
    "consultar_listas_restrictivas",
    "buscar_noticias",
    "consultar_riesgo_categoria",
    "registrar_informe",
    "escalar_a_cumplimiento",
}

VALID_CALLS = {
    "consultar_registro_mercantil": {"consulta": "CO-TV-0001"},
    "consultar_listas_restrictivas": {"tipo": "persona", "referencia": "PE-0003"},
    "buscar_noticias": {"consulta": "Tienda Verde"},
    "consultar_riesgo_categoria": {"categoria": "apuestas"},
    "registrar_informe": {
        "comercio_id": "CO-LB-0002",
        "recomendacion": "habilitar",
        "hallazgos": {"registro": {"fuente": "registro_mercantil_ficticio"}},
        "cobertura": {"cubiertos": ["registro"], "sin_cubrir": []},
    },
    "escalar_a_cumplimiento": {
        "comercio_id": "CO-TV-0001",
        "hallazgos": {"riesgo": {"fuente": "catalogo_riesgo_ficticio"}},
        "cobertura": {"cubiertos": ["riesgo"], "sin_cubrir": []},
        "causa": "alto riesgo",
        "accion_recomendada": "revisión manual",
    },
}


def test_exactly_the_six_contract_tools_are_registered():
    tools = asyncio.run(server.list_tools())
    assert {t.name for t in tools} == EXPECTED and len(tools) == 6


def test_registered_descriptions_are_the_contract_text():
    tools = {t.name: t.description for t in asyncio.run(server.list_tools())}
    assert "NO elijas" in tools["consultar_registro_mercantil"]
    assert "NO es una coincidencia en listas" in tools["buscar_noticias"]


def test_every_tool_returns_content_separated_from_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("PASARELA_RUNTIME_DIR", str(tmp_path))
    for name, args in VALID_CALLS.items():
        result = asyncio.run(server.call_tool(name, args))
        body = result.structured_content
        assert body["ok"] is True, name
        assert "content" in body, name
        assert body["metadata"]["source"] and body["metadata"]["fetched_at"], name
        assert "source" not in body["content"] and "fetched_at" not in body["content"], name
