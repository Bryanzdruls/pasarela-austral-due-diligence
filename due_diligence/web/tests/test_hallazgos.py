"""Hallazgos visibles (FR-014) y formato del coordinador (FR-013), sin modelo ni navegador.

El hallazgo sale del sobre `ok: true` que devolvió el servidor, nunca de lo que cuente el modelo.
"""

import json

import pytest

from due_diligence.events import CoordinatorText, FrontFinding, FrontName
from due_diligence.web.markdown import a_bloques
from due_diligence.web.observadores import observador_post
from due_diligence.web.vista import a_vista

PREFIX = "mcp__pasarela-fuentes__"
REGISTRO = "consultar_registro_mercantil"
LISTAS = "consultar_listas_restrictivas"
NOTICIAS = "buscar_noticias"
RIESGO = "consultar_riesgo_categoria"
INTERNOS = ("mcp__", "match_count", "ambiguous", "ok:", "tool_use_id", "{", "}")


FECHA = "2026-10-17T12:00:00+00:00"


def envelope(content, ok=True, metadata=None):
    metadata = {"source": "x_ficticio", "fetched_at": FECHA} if metadata is None else metadata
    return json.dumps({"ok": ok, "content": content, "metadata": metadata})


async def observar(tool, content, ok=True, prefix=PREFIX, entrada=None):
    emitted = []
    datos = {
        "tool_name": prefix + tool,
        "tool_input": entrada or {},
        "tool_response": envelope(content, ok),
    }
    assert await observador_post(emitted.append)(datos, "t", None) == {}
    return emitted


def comercio(id_="CO-XX-0001", estado="activo", conflictos=()):
    return {
        "id": id_,
        "razon_social": "Comercio Uno SAS",
        "estado": estado,
        "representante_legal": {"id": "PE-0001", "nombre": "Persona Ficticia Uno"},
        "conflicts": list(conflictos),
    }


def registro(*comercios):
    return {
        "match_count": len(comercios),
        "ambiguous": len(comercios) > 1,
        "matches": list(comercios),
    }


async def un_hallazgo(tool, content):
    (evento,) = await observar(tool, content)
    assert isinstance(evento, FrontFinding)
    assert not any(t in evento.resumen for t in INTERNOS), evento.resumen
    return evento


# --------------------------------------------------------------------------- registro


async def test_a_unique_registry_match_says_who_it_is_and_who_represents_it():
    evento = await un_hallazgo(REGISTRO, registro(comercio()))
    assert evento.frente is FrontName.REGISTRO_MERCANTIL
    for dato in ("CO-XX-0001", "Comercio Uno SAS", "activo", "Persona Ficticia Uno"):
        assert dato in evento.resumen


async def test_several_registry_matches_list_every_candidate_and_ask_for_the_identifier():
    evento = await un_hallazgo(REGISTRO, registro(comercio("CO-XX-0004"), comercio("CO-XX-0005")))
    assert "2 comercios" in evento.resumen
    assert "CO-XX-0004" in evento.resumen and "CO-XX-0005" in evento.resumen
    assert "identificador" in evento.resumen.lower()


async def test_no_registry_match_says_so():
    evento = await un_hallazgo(REGISTRO, registro())
    assert "ningún comercio" in evento.resumen.lower()


async def test_a_registry_conflict_is_part_of_the_finding():
    evento = await un_hallazgo(REGISTRO, registro(comercio(conflictos=["fecha_constitucion"])))
    assert "fechas de constitución distintas" in evento.resumen


# --------------------------------------------------------------------------- listas


async def test_a_list_match_names_the_list():
    contenido = {
        "match": True,
        "entradas": [{"nombre_lista": "lista_ficticia_a", "fecha_inclusion": "2025-01-01"}],
    }
    evento = await un_hallazgo(LISTAS, contenido)
    assert evento.frente is FrontName.LISTAS_RESTRICTIVAS
    assert "coincidencia" in evento.resumen.lower() and "lista_ficticia_a" in evento.resumen


async def test_no_list_match_says_so_and_does_not_look_like_a_match():
    evento = await un_hallazgo(LISTAS, {"match": False, "entradas": []})
    assert evento.resumen.lower().startswith("sin coincidencias")


# --------------------------------------------------------------------------- noticias y riesgo


@pytest.mark.parametrize(
    "menciones, esperado",
    [(0, "sin menciones"), (1, "1 mención"), (3, "3 menciones")],
)
async def test_news_say_how_many_mentions_there_are(menciones, esperado):
    contenido = {"menciones": [{"titular": f"t{i}"} for i in range(menciones)]}
    evento = await un_hallazgo(NOTICIAS, contenido)
    assert evento.frente is FrontName.NOTICIAS
    assert esperado in evento.resumen.lower()


async def test_the_category_risk_is_stated():
    evento = await un_hallazgo(RIESGO, {"categoria": "suplementos dietarios", "riesgo": "alto"})
    assert evento.frente is FrontName.RIESGO_CATEGORIA
    assert "suplementos dietarios" in evento.resumen and "alto" in evento.resumen


# ---------------------------------------------------------------------- lo que no es hallazgo


@pytest.mark.parametrize(
    "tipo, referencia, sujeto",
    [
        ("comercio", "CO-XX-0001", "el comercio CO-XX-0001"),
        ("persona", "PE-0003", "la persona PE-0003"),
    ],
)
async def test_a_list_finding_says_who_was_checked(tipo, referencia, sujeto):
    entrada = {"tipo": tipo, "referencia": referencia}
    (sin,) = await observar(LISTAS, {"match": False, "entradas": []}, entrada=entrada)
    assert sin.resumen == f"Sin coincidencias en las listas restrictivas para {sujeto}."
    con = {"match": True, "entradas": [{"nombre_lista": "lista_ficticia_a"}]}
    (hay,) = await observar(LISTAS, con, entrada=entrada)
    assert sujeto in hay.resumen and "lista_ficticia_a" in hay.resumen


async def test_a_news_finding_says_what_was_searched():
    entrada = {"consulta": "Tienda Verde SAS"}
    (sin,) = await observar(NOTICIAS, {"menciones": []}, entrada=entrada)
    assert sin.resumen == 'Sin menciones en las noticias para "Tienda Verde SAS".'
    (con,) = await observar(NOTICIAS, {"menciones": [{}]}, entrada={"consulta": "CO-XX-0001"})
    assert con.resumen == '1 mención en las noticias para "CO-XX-0001".'


async def test_the_searched_text_is_trimmed_and_flattened():
    entrada = {"consulta": "uno\ndos\t" + "x" * 300}
    (evento,) = await observar(NOTICIAS, {"menciones": []}, entrada=entrada)
    assert "\n" not in evento.resumen and "\t" not in evento.resumen
    assert len(evento.resumen) < 140 and "…" in evento.resumen


@pytest.mark.parametrize(
    "entrada",
    [
        {"tipo": 5, "referencia": None},
        {"tipo": "otro", "referencia": "X"},
        {"referencia": "PE-1"},
        [],
    ],
)
async def test_an_unusable_query_input_falls_back_to_the_plain_finding(entrada):
    (evento,) = await observar(LISTAS, {"match": False, "entradas": []}, entrada=entrada or None)
    assert evento.resumen == "Sin coincidencias en las listas restrictivas."


@pytest.mark.parametrize("tool", [REGISTRO, LISTAS, NOTICIAS, RIESGO])
async def test_a_failed_query_produces_no_finding(tool):
    assert await observar(tool, {"codigo": "unavailable", "reintentable": True}, ok=False) == []


@pytest.mark.parametrize(
    "tool, contenido",
    [
        (REGISTRO, registro(comercio())),
        (LISTAS, {"match": False, "entradas": []}),
        (NOTICIAS, {"menciones": []}),
        (RIESGO, {"categoria": "libros", "riesgo": "bajo"}),
    ],
)
async def test_a_failed_response_with_a_valid_looking_content_still_produces_no_finding(
    tool, contenido
):
    # Lo que decide es `ok`, no que el contenido parezca un resultado.
    assert await observar(tool, contenido, ok=False) == []


@pytest.mark.parametrize(
    "tool, contenido",
    [
        (REGISTRO, {"otra": "cosa"}),
        (REGISTRO, {"matches": "no es una lista"}),
        (LISTAS, {"entradas": []}),
        (NOTICIAS, {"menciones": "x"}),
        (RIESGO, {"riesgo": 5}),
        (RIESGO, []),
    ],
)
async def test_an_unexpected_shape_produces_no_finding_instead_of_inventing_one(tool, contenido):
    assert await observar(tool, contenido) == []


async def test_an_unreadable_response_or_a_foreign_tool_produces_no_finding():
    emitted = []
    hook = observador_post(emitted.append)
    for respuesta in ("no es json", "", None, 42):
        await hook({"tool_name": PREFIX + LISTAS, "tool_response": respuesta}, "t", None)
    await hook({"tool_name": PREFIX + "otra_herramienta", "tool_response": envelope({})}, "t", None)
    assert emitted == []


async def test_the_short_tool_name_also_produces_a_finding():
    (evento,) = await observar(RIESGO, {"categoria": "libros", "riesgo": "bajo"}, prefix="")
    assert evento.frente is FrontName.RIESGO_CATEGORIA


async def test_a_failing_emit_never_breaks_the_hook():
    def boom(evento):
        raise RuntimeError("la interfaz falló")

    datos = {
        "tool_name": PREFIX + RIESGO,
        "tool_response": envelope({"categoria": "libros", "riesgo": "bajo"}),
    }
    assert await observador_post(boom)(datos, "t", None) == {}


# --------------------------------------------------------------------------- vista


async def test_a_finding_carries_the_source_and_date_the_server_stamped():
    """La procedencia sale del sobre del servidor, no de lo que escriba el subagente."""
    evento = await un_hallazgo(RIESGO, {"categoria": "libros", "riesgo": "bajo"})
    assert (evento.fuente, evento.fecha) == ("x_ficticio", FECHA)


@pytest.mark.parametrize("metadata", [{}, {"source": 5, "fetched_at": None}, "texto", []])
async def test_a_finding_without_usable_metadata_is_still_shown_without_provenance(metadata):
    datos = {
        "tool_name": PREFIX + RIESGO,
        "tool_input": {},
        "tool_response": envelope({"categoria": "libros", "riesgo": "bajo"}, metadata=metadata),
    }
    emitted = []
    await observador_post(emitted.append)(datos, "t", None)
    assert len(emitted) == 1 and (emitted[0].fuente, emitted[0].fecha) == ("", "")


def test_the_finding_card_shows_the_provenance_the_server_gave():
    evento = FrontFinding(
        FrontName.REGISTRO_MERCANTIL,
        "Ningún comercio coincide.",
        fuente="registro_ficticio",
        fecha=FECHA,
    )
    assert a_vista(evento, 1)["detalle"] == (
        f"Ningún comercio coincide. Fuente: registro_ficticio. Fecha: {FECHA}."
    )


def test_the_finding_card_never_invents_a_provenance_it_was_not_given():
    detalle = a_vista(FrontFinding(FrontName.NOTICIAS, "Sin menciones."), 1)["detalle"]
    assert detalle == "Sin menciones." and "Fuente" not in detalle


def test_the_finding_card_names_the_front_and_carries_the_summary():
    evento = FrontFinding(FrontName.LISTAS_RESTRICTIVAS, "Sin coincidencias en listas.")
    vista = a_vista(evento, 7)
    assert vista["tipo"] == "hallazgo" and vista["n"] == 7
    assert vista["titulo"] == "Hallazgo en las listas restrictivas"
    assert vista["detalle"] == "Sin coincidencias en listas."
    assert vista["extra"] == {"frente": "listas_restrictivas"}
    assert vista["hora"] == evento.timestamp


@pytest.mark.parametrize("frente", list(FrontName))
def test_every_front_has_a_plain_finding_title(frente):
    titulo = a_vista(FrontFinding(frente, "x"), 1)["titulo"]
    assert titulo.startswith("Hallazgo en ") and "_" not in titulo


def test_the_coordinator_card_keeps_the_text_and_adds_its_formatted_blocks():
    texto = "## Recomendación\n**Por qué:** riesgo alto.\n\n- uno\n- dos"
    vista = a_vista(CoordinatorText(texto), 3)
    assert vista["tipo"] == "coordinador" and vista["detalle"] == texto
    assert vista["extra"]["bloques"] == a_bloques(texto)
    assert [b["t"] for b in vista["extra"]["bloques"]] == ["titulo", "parrafo", "lista"]


def test_only_the_coordinator_card_carries_blocks():
    assert "bloques" not in a_vista(FrontFinding(FrontName.NOTICIAS, "Sin menciones."), 1)["extra"]
