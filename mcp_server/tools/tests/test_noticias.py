from mcp_server.tools import listas, noticias


def test_commerce_mentions_by_id_and_by_name():
    by_id = noticias.buscar_noticias("CO-TV-0001")["content"]["menciones"]
    by_name = noticias.buscar_noticias("tienda verde")["content"]["menciones"]
    assert len(by_id) == 1 and by_id == by_name
    m = by_id[0]
    assert {"titular", "fecha", "fuente", "resumen"} <= set(m)


def test_person_mention_is_not_a_list_match():
    menciones = noticias.buscar_noticias("Rosa Noticia Prado")["content"]["menciones"]
    assert len(menciones) == 1
    assert listas.consultar_listas_restrictivas("persona", "PE-0007")["content"]["match"] is False


def test_no_mentions_is_not_an_error():
    r = noticias.buscar_noticias("Libros del Faro")
    assert r["ok"] is True and r["content"]["menciones"] == []


def test_metadata_source():
    assert noticias.buscar_noticias("CO-TV-0001")["metadata"]["source"] == "noticias_ficticias"


def test_blank_query_is_invalid():
    r = noticias.buscar_noticias("  ")
    assert r["ok"] is False and r["error_code"] == "invalid_input"


def test_description_says_mention_is_not_a_list_match():
    d = noticias.DESCRIPTION
    assert "NO es una coincidencia en listas" in d
    assert "consultar_listas_restrictivas" in d
