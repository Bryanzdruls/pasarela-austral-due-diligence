from mcp_server.tools import listas


def test_person_in_list_matches_with_origin_and_date():
    r = listas.consultar_listas_restrictivas("persona", "PE-0003")
    assert r["ok"] is True and r["content"]["match"] is True
    entrada = r["content"]["entradas"][0]
    assert entrada["nombre_lista"] == "lista_restrictiva_ficticia_a"
    assert entrada["fecha_inclusion"] == "2024-03-01"
    assert r["metadata"]["source"] == "listas_restrictivas_ficticias"


def test_clean_commerce_has_no_match():
    r = listas.consultar_listas_restrictivas("comercio", "CO-LB-0002")
    assert r["content"] == {"match": False, "entradas": []}


def test_unknown_or_wrong_type_reference_is_rejected_not_reported_clean():
    for tipo, ref in (
        ("comercio", "PE-0003"),
        ("persona", "PE-9999"),
        ("persona", "Héctor Muestra Lista"),
    ):
        r = listas.consultar_listas_restrictivas(tipo, ref)
        assert r["ok"] is False and r["error_code"] == "invalid_input", (tipo, ref)


def test_invalid_input():
    for args in (("persona", ""), ("persona", "  "), ("otro", "PE-0003")):
        r = listas.consultar_listas_restrictivas(*args)
        assert r["ok"] is False and r["error_code"] == "invalid_input"


def test_description_requires_identified_commerce_and_separates_news():
    d = listas.DESCRIPTION
    assert "identificado de forma unívoca" in d
    assert "noticia" in d and "NO" in d
