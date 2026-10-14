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


def test_same_reference_with_other_type_does_not_match():
    assert listas.consultar_listas_restrictivas("comercio", "PE-0003")["content"]["match"] is False


def test_invalid_input():
    for args in (("persona", ""), ("persona", "  "), ("otro", "PE-0003")):
        r = listas.consultar_listas_restrictivas(*args)
        assert r["ok"] is False and r["error_code"] == "invalid_input"


def test_description_requires_identified_commerce_and_separates_news():
    d = listas.DESCRIPTION
    assert "identificado de forma unívoca" in d
    assert "noticia" in d and "NO" in d
