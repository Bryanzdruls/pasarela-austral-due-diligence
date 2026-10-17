"""Los documentos de cara al evaluador: README, DECISIONES.md y el guion del video.

El comprobador se prueba con árboles sintéticos; además, una prueba lo ejecuta contra el
repositorio real, de modo que `pytest` vigile que los documentos no se rompan.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
import verify_docs as vd

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "scripts" / "verify_docs.py"
PROJECT = "https://github.com/users/Bryanzdruls/projects/4"

SECCIONES = [
    "Qué es",
    "Requisitos",
    "Cómo correrlo",
    "Pruebas",
    "Los siete casos",
    "Enlaces",
    "Mapa de piezas",
    "Límites conocidos",
]


def readme(video="PENDIENTE", enlace=PROJECT, secciones=None, extra=""):
    secciones = SECCIONES if secciones is None else secciones
    partes = ["# Proyecto\n"]
    for titulo in secciones:
        partes.append(f"## {titulo}\n")
        if titulo == "Cómo correrlo":
            partes.append("Corre `scripts/hacer.py` y mira `docs/CASOS.md`.\n")
        elif titulo == "Enlaces":
            partes.append(
                f"- **GitHub Project**: {enlace}\n- **Video de funcionamiento**: {video}\n"
            )
        else:
            partes.append("Texto breve.\n")
    return "\n".join(partes) + extra


def decisiones(filas=range(1, 12), relleno="", celdas=None):
    celdas = celdas or {}
    cabecera = (
        "| # | Necesidad | Mecanismo | Por qué | Alternativa descartada |\n|---|---|---|---|---|\n"
    )
    cuerpo = ""
    for n in filas:
        c = celdas.get(n, ["necesidad", "mecanismo `scripts/hacer.py`", "motivo", "alternativa"])
        cuerpo += f"| {n} | " + " | ".join(c) + " |\n"
    return "# Decisiones\n\nIntroducción breve.\n\n" + cabecera + cuerpo + "\n" + relleno + "\n"


IDS = {1: "CO-TV-0001", 2: "CO-LB-0002", 3: "CO-DA-0003", 4: "CO-CA-0004", 5: "", 6: "CO-LB-0002"}
IDS[7] = "CO-FH-0006"
GUION_SECCIONES = ["Antes de grabar", "Qué no mostrar", "Si el modelo varía"]


def casos():
    filas = ""
    for n in range(1, 8):
        datos = f"`{IDS[n]}`" if IDS[n] else "cualquiera"
        if n == 4:
            datos = "`CO-CA-0004` y `CO-CA-0005`"
        filas += f'| {n} | Caso {n} | "mensaje del caso {n}" | {datos} | resultado |\n'
    cabecera = "| # | Caso | Mensaje | Datos | Resultado |\n|---|---|---|---|---|\n"
    return "# Casos\n\n" + cabecera + filas


def guion(tiempos=None, sin_caso=None, sin_id=None, secciones=None):
    tiempos = tiempos or ["0:20", *["0:35"] * 7, "0:15"]  # introducción, siete casos y cierre
    secciones = GUION_SECCIONES if secciones is None else secciones
    filas = [f"| Introducción | — | La página vacía | {tiempos[0]} |"]
    for n in range(1, 8):
        if n == sin_caso:
            continue
        identificador = "" if n == sin_id else f" ({IDS[n] or 'CO-TV-0001'})"
        filas.append(f"| {n} | Mensaje del caso {n}{identificador} | Lo que se ve | {tiempos[n]} |")
    filas.append(f"| Cierre | — | Resumen | {tiempos[8]} |")
    cuerpo = "# Guion del video\n\n"
    for titulo in secciones:
        cuerpo += f"## {titulo}\n\n- punto\n\n"
    cuerpo += "## Guion\n\n| Caso | Mensaje | Qué debe verse | Tiempo |\n|---|---|---|---|\n"
    return cuerpo + "\n".join(filas) + "\n"


def arbol(
    tmp_path,
    readme_texto=None,
    decisiones_texto=None,
    archivos=("scripts/hacer.py",),
    casos_texto=None,
    video_texto=None,
):
    for rel in archivos:
        ruta = tmp_path / rel
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text("x", encoding="utf-8")
    (tmp_path / "docs").mkdir(exist_ok=True)
    if casos_texto is not False:
        (tmp_path / "docs" / "CASOS.md").write_text(
            casos() if casos_texto is None else casos_texto, encoding="utf-8"
        )
    if video_texto is not False:
        (tmp_path / "docs" / "VIDEO.md").write_text(
            guion() if video_texto is None else video_texto, encoding="utf-8"
        )
    if readme_texto is not False:
        (tmp_path / "README.md").write_text(
            readme() if readme_texto is None else readme_texto, encoding="utf-8"
        )
    if decisiones_texto is not False:
        (tmp_path / "DECISIONES.md").write_text(
            decisiones() if decisiones_texto is None else decisiones_texto, encoding="utf-8"
        )
    return tmp_path


def fallos(raiz):
    return {c.name: c.detail for c in vd.check_all(raiz) if not c.ok}


# --------------------------------------------------------------------------- árbol completo


def test_a_valid_tree_passes_every_check(tmp_path):
    arbol(tmp_path)
    assert fallos(tmp_path) == {}


def test_every_check_is_reported_with_its_stable_name(tmp_path):
    arbol(tmp_path)
    assert {c.name for c in vd.check_all(tmp_path)} == set(vd.ALL_CHECKS)


# --------------------------------------------------------------------------- README


def test_a_missing_readme_fails(tmp_path):
    arbol(tmp_path, readme_texto=False)
    assert vd.CHECK_README in fallos(tmp_path)


@pytest.mark.parametrize("quitar", SECCIONES)
def test_a_missing_required_section_fails_and_is_named(tmp_path, quitar):
    arbol(tmp_path, readme(secciones=[s for s in SECCIONES if s != quitar]))
    problemas = fallos(tmp_path)
    assert vd.CHECK_README in problemas
    assert quitar.lower().split()[-1][:5] in problemas[vd.CHECK_README].lower()


def test_sections_are_found_regardless_of_case_and_accents(tmp_path):
    secciones = [
        "QUE ES",
        "requisitos",
        "COMO CORRERLO",
        "Pruebas",
        "CASOS",
        "ENLACES",
        "MAPA",
        "limites",
    ]
    arbol(tmp_path, readme(secciones=secciones))
    assert vd.CHECK_README not in fallos(tmp_path)


def test_a_readme_without_the_project_link_fails(tmp_path):
    arbol(tmp_path, readme(enlace="(sin enlace)"))
    problemas = fallos(tmp_path)
    assert vd.CHECK_README_LINKS in problemas and "Project" in problemas[vd.CHECK_README_LINKS]


# --------------------------------------------------------------------------- video


@pytest.mark.parametrize(
    "video, estado",
    [("PENDIENTE", "pendiente"), ("https://ejemplo.invalid/v", "publicado")],
)
def test_a_pending_or_published_video_link_passes_and_reports_its_state(tmp_path, video, estado):
    arbol(tmp_path, readme(video=video))
    estados = {c.name: c for c in vd.check_all(tmp_path)}
    assert estados[vd.CHECK_VIDEO_STATE].ok and estado in estados[vd.CHECK_VIDEO_STATE].detail


@pytest.mark.parametrize("video", ["PENDIENTE https://ejemplo.invalid/v", "", "próximamente"])
def test_an_inconsistent_video_link_fails(tmp_path, video):
    arbol(tmp_path, readme(video=video))
    assert vd.CHECK_VIDEO_STATE in fallos(tmp_path)


def test_a_readme_without_a_video_line_fails_the_video_state(tmp_path):
    arbol(tmp_path, readme().replace("Video de funcionamiento", "Otra cosa"))
    problemas = fallos(tmp_path)
    assert vd.CHECK_VIDEO_STATE in problemas and "ausente" in problemas[vd.CHECK_VIDEO_STATE]


# --------------------------------------------------------------------------- rutas citadas


def test_a_cited_path_that_does_not_exist_fails_and_is_named_with_its_document(tmp_path):
    arbol(tmp_path, readme(extra="\nMira `docs/inventado.md`.\n"))
    problemas = fallos(tmp_path)
    assert (
        "docs/inventado.md" in problemas[vd.CHECK_PATHS]
        and "README.md" in problemas[vd.CHECK_PATHS]
    )


def test_a_path_cited_by_decisiones_is_checked_too(tmp_path):
    celdas = {3: ["n", "usa `scripts/fantasma.py`", "porque", "otra"]}
    arbol(tmp_path, decisiones_texto=decisiones(celdas=celdas))
    problemas = fallos(tmp_path)
    assert (
        "scripts/fantasma.py" in problemas[vd.CHECK_PATHS]
        and "DECISIONES.md" in problemas[vd.CHECK_PATHS]
    )


@pytest.mark.parametrize(
    "ignorada",
    [
        "python -m uv run pytest -q",
        "specs/NNN-*/spec.md",
        "docs/*.md",
        "scripts/hacer.py#seccion",
        "scripts/hacer.py:12",
        "scripts/",
        "/api/estado",
        "https://ejemplo.invalid/docs/inventado.md",
        "due_diligence.web",
        "--puerto",
        "ANTHROPIC_API_KEY",
        "127.0.0.1:8000",
        "<carpeta>/x.py",
    ],
)
def test_commands_globs_routes_urls_and_fragments_are_not_checked_as_missing_files(
    tmp_path, ignorada
):
    arbol(tmp_path, readme(extra=f"\nEjemplo: `{ignorada}`.\n"))
    assert vd.CHECK_PATHS not in fallos(tmp_path), ignorada


def test_a_directory_with_a_trailing_slash_is_checked_as_a_directory(tmp_path):
    arbol(tmp_path, readme(extra="\nVer `scripts/` y `docs/falta/`.\n"))
    problemas = fallos(tmp_path)
    assert (
        "docs/falta" in problemas[vd.CHECK_PATHS] and "`scripts/`" not in problemas[vd.CHECK_PATHS]
    )


# --------------------------------------------------------------------------- tabla de decisiones


def test_ten_rows_fail_and_the_missing_one_is_named(tmp_path):
    arbol(tmp_path, decisiones_texto=decisiones(filas=[n for n in range(1, 12) if n != 7]))
    problemas = fallos(tmp_path)
    assert vd.CHECK_DECISIONES_TABLE in problemas and "7" in problemas[vd.CHECK_DECISIONES_TABLE]


def test_a_repeated_row_fails(tmp_path):
    arbol(tmp_path, decisiones_texto=decisiones(filas=[*range(1, 12), 4]))
    assert vd.CHECK_DECISIONES_TABLE in fallos(tmp_path)


def test_a_row_outside_one_to_eleven_fails(tmp_path):
    arbol(tmp_path, decisiones_texto=decisiones(filas=[*range(1, 11), 12]))
    assert vd.CHECK_DECISIONES_TABLE in fallos(tmp_path)


@pytest.mark.parametrize("posicion", [0, 1, 2, 3])
def test_an_empty_cell_fails_and_names_the_row(tmp_path, posicion):
    base = ["necesidad", "mecanismo", "motivo", "alternativa"]
    base[posicion] = "  "
    arbol(tmp_path, decisiones_texto=decisiones(celdas={5: base}))
    problemas = fallos(tmp_path)
    assert vd.CHECK_DECISIONES_TABLE in problemas and "5" in problemas[vd.CHECK_DECISIONES_TABLE]


def test_a_missing_decisiones_file_fails_both_decisiones_checks(tmp_path):
    arbol(tmp_path, decisiones_texto=False)
    problemas = fallos(tmp_path)
    assert vd.CHECK_DECISIONES_TABLE in problemas and vd.CHECK_DECISIONES_LENGTH in problemas


# --------------------------------------------------------------------------- extensión


def test_word_count_ignores_code_blocks_markdown_syntax_and_table_separators():
    texto = (
        "# Título de prueba\n\n```python\nuno dos tres cuatro\n```\n\n"
        "| a | b |\n|---|---|\n| **x** | `y` |\n"
    )
    assert vd.word_count(texto) == 7  # título (3) y las celdas a, b, x, y; el código no cuenta


def test_a_document_with_exactly_one_thousand_words_passes_and_one_more_fails(tmp_path):
    base = decisiones()
    exacto = base + " ".join(["palabra"] * (vd.MAX_WORDS - vd.word_count(base)))
    assert vd.word_count(exacto) == vd.MAX_WORDS == 1000
    arbol(tmp_path, decisiones_texto=exacto)
    assert vd.CHECK_DECISIONES_LENGTH not in fallos(tmp_path)
    (tmp_path / "DECISIONES.md").write_text(exacto + " de_mas", encoding="utf-8")
    problemas = fallos(tmp_path)
    assert (
        vd.CHECK_DECISIONES_LENGTH in problemas and "1001" in problemas[vd.CHECK_DECISIONES_LENGTH]
    )


def test_words_inside_code_blocks_do_not_count_toward_the_limit(tmp_path):
    base = decisiones()
    bloque = "```\n" + " ".join(["codigo"] * 3000) + "\n```\n"
    arbol(tmp_path, decisiones_texto=base + bloque)
    assert vd.CHECK_DECISIONES_LENGTH not in fallos(tmp_path)


# --------------------------------------------------------------------------- guion del video


def test_a_valid_script_passes_and_is_reported(tmp_path):
    arbol(tmp_path)
    estados = {c.name: c for c in vd.check_all(tmp_path)}
    assert estados[vd.CHECK_GUION].ok and "4:40" in estados[vd.CHECK_GUION].detail


def test_exactly_five_minutes_passes_and_one_second_more_fails(tmp_path):
    justo = ["0:20", *["0:35"] * 6, "0:55", "0:15"]  # 0:20 + 6x0:35 + 0:55 + 0:15 = 5:00
    arbol(tmp_path, video_texto=guion(tiempos=justo))
    assert vd.CHECK_GUION not in fallos(tmp_path)
    pasado = [*justo[:-1], "0:16"]
    arbol(tmp_path, video_texto=guion(tiempos=pasado))
    problemas = fallos(tmp_path)
    assert vd.CHECK_GUION in problemas and "5:01" in problemas[vd.CHECK_GUION]


@pytest.mark.parametrize("falta", range(1, 8))
def test_a_missing_case_fails_and_is_named(tmp_path, falta):
    arbol(tmp_path, video_texto=guion(sin_caso=falta))
    problemas = fallos(tmp_path)
    assert vd.CHECK_GUION in problemas and f"caso {falta}" in problemas[vd.CHECK_GUION].lower()


@pytest.mark.parametrize("caso", [1, 2, 3, 4, 6, 7])
def test_a_case_without_its_fictitious_identifier_fails_and_is_named(tmp_path, caso):
    arbol(tmp_path, video_texto=guion(sin_id=caso))
    problemas = fallos(tmp_path)
    assert vd.CHECK_GUION in problemas and f"caso {caso}" in problemas[vd.CHECK_GUION].lower()


def test_case_four_is_satisfied_by_either_of_its_two_candidates(tmp_path):
    texto = guion(sin_id=4).replace("Mensaje del caso 4", "Mensaje del caso 4 (CO-CA-0005)")
    arbol(tmp_path, video_texto=texto)
    assert vd.CHECK_GUION not in fallos(tmp_path)


def test_a_case_without_data_in_the_cases_document_needs_no_identifier(tmp_path):
    arbol(tmp_path, video_texto=guion(sin_id=5))
    assert vd.CHECK_GUION not in fallos(tmp_path)


def test_a_row_without_a_readable_time_fails_and_is_named(tmp_path):
    arbol(
        tmp_path,
        video_texto=guion().replace(
            "| Lo que se ve | 0:35 |", "| Lo que se ve | medio minuto |", 1
        ),
    )
    problemas = fallos(tmp_path)
    assert vd.CHECK_GUION in problemas and "tiempo" in problemas[vd.CHECK_GUION].lower()


@pytest.mark.parametrize("quitar", GUION_SECCIONES)
def test_a_missing_section_of_the_script_fails_and_is_named(tmp_path, quitar):
    arbol(tmp_path, video_texto=guion(secciones=[s for s in GUION_SECCIONES if s != quitar]))
    problemas = fallos(tmp_path)
    assert (
        vd.CHECK_GUION in problemas
        and quitar.lower().split()[-1][:4] in problemas[vd.CHECK_GUION].lower()
    )


def test_a_missing_script_or_cases_document_fails(tmp_path):
    arbol(tmp_path, video_texto=False)
    assert "VIDEO.md" in fallos(tmp_path)[vd.CHECK_GUION]
    (tmp_path / "docs" / "VIDEO.md").write_text(guion(), encoding="utf-8")
    (tmp_path / "docs" / "CASOS.md").unlink()
    assert "CASOS.md" in fallos(tmp_path)[vd.CHECK_GUION]


# --------------------------------------------------------------------------- línea de órdenes


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, encoding="utf-8"
    )


def test_the_cli_exits_0_on_a_valid_tree_and_1_otherwise(tmp_path):
    arbol(tmp_path)
    ok = run_cli("--root", str(tmp_path))
    assert ok.returncode == 0 and "FALLA" not in ok.stdout
    (tmp_path / "README.md").unlink()
    mal = run_cli("--root", str(tmp_path))
    assert mal.returncode == 1 and "FALLA" in mal.stdout and vd.CHECK_README in mal.stdout


def test_json_output_is_a_valid_object_with_every_check(tmp_path):
    arbol(tmp_path)
    datos = json.loads(run_cli("--root", str(tmp_path), "--json").stdout)
    assert datos["ok"] is True
    assert {c["name"] for c in datos["checks"]} == set(vd.ALL_CHECKS)


# --------------------------------------------------------------------------- el repositorio real


def test_the_real_documents_pass_every_check():
    problemas = fallos(RAIZ)
    assert problemas == {}, problemas
