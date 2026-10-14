from mcp_server.tools import registro


def test_single_match_by_id():
    r = registro.consultar_registro_mercantil("CO-TV-0001")
    assert r["ok"] is True
    c = r["content"]
    assert c["match_count"] == 1 and c["ambiguous"] is False
    m = c["matches"][0]
    assert m["razon_social"] == "Tienda Verde SAS"
    assert m["estado"] == "activo" and m["existe"] is True
    assert m["representante_legal"]["nombre"] == "Elena Prueba Ríos"
    assert m["volumen_mensual_estimado"] == 80000000
    assert r["metadata"]["source"] == "registro_mercantil_ficticio"
    assert m["conflicts"] == []


def test_match_by_name_is_case_and_accent_insensitive():
    r = registro.consultar_registro_mercantil("tienda VERDE")
    assert r["content"]["match_count"] == 1


def test_similar_names_return_all_and_flag_ambiguity():
    c = registro.consultar_registro_mercantil("Cafetería Aurora")["content"]
    assert c["match_count"] == 2 and c["ambiguous"] is True
    assert {m["id"] for m in c["matches"]} == {"CO-CA-0004", "CO-CA-0005"}


def test_no_match_is_not_an_error():
    r = registro.consultar_registro_mercantil("Comercio Que No Existe")
    assert r["ok"] is True
    assert r["content"] == {"match_count": 0, "ambiguous": False, "matches": []}


def test_conflicting_dates_are_reported_with_their_source():
    m = registro.consultar_registro_mercantil("CO-FH-0006")["content"]["matches"][0]
    dates = {f["source"]: f["fecha_constitucion"] for f in m["fuentes_registro"]}
    assert dates == {
        "registro_mercantil_ficticio": "2016-03-14",
        "camara_comercio_alterna_ficticia": "2017-03-14",
    }
    assert m["conflicts"] == ["fecha_constitucion"]


def test_blank_or_suffix_only_query_is_invalid():
    for q in ("", "   ", "SAS", "S.A.S."):
        r = registro.consultar_registro_mercantil(q)
        assert r["ok"] is False and r["error_code"] == "invalid_input"
        assert r["retryable"] is False


def test_description_tells_what_to_do_with_several_matches():
    d = registro.DESCRIPTION
    assert "NO elijas" in d and "identificador" in d
