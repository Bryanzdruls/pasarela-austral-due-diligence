"""El formato del coordinador viaja como bloques de datos: nunca como HTML (FR-013, FR-010)."""

import json

import pytest

from due_diligence.web.markdown import MAX_BLOQUES, a_bloques


def texto(v):
    return {"t": "texto", "v": v}


def negrita(v):
    return {"t": "negrita", "v": v}


def codigo(v):
    return {"t": "codigo", "v": v}


def test_plain_text_is_a_single_paragraph():
    assert a_bloques("Hola, analista.") == [{"t": "parrafo", "inline": [texto("Hola, analista.")]}]


def test_empty_or_non_text_input_gives_no_blocks():
    assert a_bloques("") == [] and a_bloques("   \n\n ") == []
    assert a_bloques(None) == [] and a_bloques(42) == []


def test_bold_and_code_are_marked_inline():
    bloques = a_bloques("Hola **mundo** y `codigo`")
    assert bloques == [
        {
            "t": "parrafo",
            "inline": [texto("Hola "), negrita("mundo"), texto(" y "), codigo("codigo")],
        }
    ]


@pytest.mark.parametrize(
    "marca", ["**sin cerrar", "`sin cerrar", "a ** ** b", "a ** b ** c", "``", "a * b"]
)
def test_unbalanced_or_empty_markers_stay_as_literal_text(marca):
    (bloque,) = a_bloques(marca)
    assert bloque["inline"] == [texto(marca)]


def test_headings_keep_their_level():
    bloques = a_bloques("# Uno\n\n## Dos **fuerte**\n\n###### Seis")
    assert [(b["t"], b["nivel"]) for b in bloques] == [("titulo", 1), ("titulo", 2), ("titulo", 6)]
    assert bloques[1]["inline"] == [texto("Dos "), negrita("fuerte")]


def test_seven_hashes_are_not_a_heading():
    (bloque,) = a_bloques("####### no es título")
    assert bloque["t"] == "parrafo"


def test_bullet_and_numbered_lists_are_separate_blocks():
    bloques = a_bloques("- uno\n- dos\n\n1. primero\n2) segundo")
    assert bloques[0] == {
        "t": "lista",
        "ordenada": False,
        "items": [[texto("uno")], [texto("dos")]],
    }
    assert bloques[1] == {
        "t": "lista",
        "ordenada": True,
        "items": [[texto("primero")], [texto("segundo")]],
    }


def test_asterisk_and_bullet_markers_also_make_lists():
    bloques = a_bloques("* a\n* b")
    assert bloques[0]["t"] == "lista" and len(bloques[0]["items"]) == 2


def test_a_table_has_a_header_and_rows():
    entrada = "| Id | Estado |\n|---|:---:|\n| **CO-1** | activo |\n| CO-2 | inactivo |"
    (tabla,) = a_bloques(entrada)
    assert tabla["t"] == "tabla"
    assert tabla["cabecera"] == [[texto("Id")], [texto("Estado")]]
    assert tabla["filas"] == [
        [[negrita("CO-1")], [texto("activo")]],
        [[texto("CO-2")], [texto("inactivo")]],
    ]


def test_pipes_without_a_separator_row_are_not_a_table():
    (bloque,) = a_bloques("| solo | una línea |")
    assert bloque["t"] == "parrafo"


def test_a_ragged_table_does_not_break_and_keeps_every_cell():
    (tabla,) = a_bloques("| a | b |\n|---|---|\n| 1 |\n| 1 | 2 | 3 |")
    assert [len(f) for f in tabla["filas"]] == [1, 3]


def test_a_horizontal_rule_is_a_separator():
    assert a_bloques("antes\n\n---\n\ndespués")[1] == {"t": "separador"}


def test_lines_of_a_paragraph_keep_their_line_breaks():
    (bloque,) = a_bloques("primera línea\nsegunda línea")
    assert bloque["inline"] == [texto("primera línea\nsegunda línea")]


def test_a_list_after_a_paragraph_without_a_blank_line_is_still_a_list():
    bloques = a_bloques("Motivos:\n- uno\n- dos")
    assert [b["t"] for b in bloques] == ["parrafo", "lista"]


@pytest.mark.parametrize(
    "peligro",
    [
        '<img src=x onerror="alert(1)">',
        "<script>alert(1)</script>",
        "[clic](javascript:alert(1))",
        "![x](http://ejemplo.invalid/a.png)",
        "<b>negrita html</b>",
    ],
)
def test_html_links_and_images_stay_as_plain_text(peligro):
    bloques = a_bloques(f"antes {peligro} después")
    plano = "".join(s["v"] for b in bloques for s in b["inline"])
    assert peligro in plano
    assert {s["t"] for b in bloques for s in b["inline"]} <= {"texto"}


def test_the_blocks_are_plain_json_data():
    bloques = a_bloques("# T\n\n| a |\n|---|\n| **b** |\n\n- x\n\n---\n\n`c`")
    assert json.loads(json.dumps(bloques, ensure_ascii=False)) == bloques


def test_a_huge_input_is_bounded():
    enorme = "\n".join(f"- elemento {i}" for i in range(5000))
    bloques = a_bloques(enorme)
    assert len(bloques) <= MAX_BLOQUES
    assert sum(len(b.get("items", [])) for b in bloques) <= 1000
    muchos = "\n\n".join(f"párrafo {i}" for i in range(5000))
    assert len(a_bloques(muchos)) == MAX_BLOQUES


def test_the_cap_is_strict_even_when_a_paragraph_closes_right_at_the_limit():
    casi_lleno = "\n\n".join(f"párrafo {i}" for i in range(MAX_BLOQUES - 1))
    for cierre in ("# titulo", "---", "- item", "| a |\n|---|\n| b |"):
        assert len(a_bloques(f"{casi_lleno}\n\nun párrafo más\n{cierre}\n\notro")) <= MAX_BLOQUES
    assert len(a_bloques("# t\n" * 500)) == MAX_BLOQUES


def test_the_real_answer_of_the_qa_is_rendered_as_structure():
    respuesta = (
        "## Datos aportados por el analista\n"
        "- Categoría que declaraste: venta en línea de suplementos dietarios.\n"
        "- Volumen mensual que estimas: $80.000.000.\n\n"
        "## Recomendación: `escalar_a_cumplimiento`\n"
        "**Por qué:** la categoría es de alto riesgo.\n\n"
        "| Id | Estado |\n|---|---|\n| **CO-CA-0004** | activo |"
    )
    tipos = [b["t"] for b in a_bloques(respuesta)]
    assert tipos == ["titulo", "lista", "titulo", "parrafo", "tabla"]
