"""Verifica los documentos de cara al evaluador: README, DECISIONES.md y el guion del video.

Uso: python scripts/verify_docs.py [--root RUTA] [--json]
Código de salida 0 si todo cumple y 1 si algo falla. Solo biblioteca estándar.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

from verify_delivery import video_state
from verify_ecosystem import Check

CHECK_README = "README completo"
CHECK_README_LINKS = "enlaces del README"
CHECK_VIDEO_STATE = "estado del enlace del video"
CHECK_PATHS = "rutas citadas existen"
CHECK_DECISIONES_TABLE = "once necesidades"
CHECK_DECISIONES_LENGTH = "extensión de DECISIONES.md"

ALL_CHECKS = (
    CHECK_README,
    CHECK_README_LINKS,
    CHECK_VIDEO_STATE,
    CHECK_PATHS,
    CHECK_DECISIONES_TABLE,
    CHECK_DECISIONES_LENGTH,
)

PROJECT_URL = "https://github.com/users/Bryanzdruls/projects/4"
# Dos páginas: una página impresa admite unas 450 a 500 palabras (plan, D5).
MAX_WORDS = 1000
NEEDS = 11
MAX_LISTED = 5
KNOWN_EXTENSIONS = (".md", ".py", ".json", ".js", ".html", ".toml")

# Secciones obligatorias del README: palabra clave (sin acentos ni mayúsculas) y cómo se nombra.
SECTIONS = {
    "que es": "qué es",
    "requisitos": "requisitos",
    "correr": "cómo correrlo",
    "pruebas": "pruebas",
    "casos": "los siete casos",
    "enlaces": "enlaces",
    "mapa": "mapa de piezas",
    "limites": "límites conocidos",
}


def _normalize(text: str) -> str:
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c)
    )
    return sin_acentos.lower()


def _read(root: Path, name: str) -> str | None:
    ruta = root / name
    return ruta.read_text(encoding="utf-8", errors="ignore") if ruta.is_file() else None


def _listed(items: list[str]) -> str:
    mostrados = ", ".join(items[:MAX_LISTED])
    return mostrados + (f" y {len(items) - MAX_LISTED} más" if len(items) > MAX_LISTED else "")


# --------------------------------------------------------------------------- README


def check_readme(root: Path) -> Check:
    texto = _read(root, "README.md")
    if texto is None:
        return Check(CHECK_README, False, "falta README.md en la raíz")
    encabezados = [_normalize(x) for x in texto.splitlines() if x.lstrip().startswith("#")]
    faltan = [
        nombre
        for clave, nombre in SECTIONS.items()
        if not any(clave in encabezado for encabezado in encabezados)
    ]
    if faltan:
        return Check(CHECK_README, False, "faltan secciones: " + ", ".join(faltan))
    return Check(CHECK_README, True, f"las {len(SECTIONS)} secciones obligatorias están")


def check_readme_links(root: Path) -> Check:
    texto = _read(root, "README.md") or ""
    if PROJECT_URL not in texto:
        return Check(
            CHECK_README_LINKS, False, f"el README no cita el GitHub Project ({PROJECT_URL})"
        )
    return Check(CHECK_README_LINKS, True, "cita el GitHub Project")


def check_video_state(root: Path) -> Check:
    estado = video_state(_read(root, "README.md") or "")
    return Check(CHECK_VIDEO_STATE, estado in ("pendiente", "publicado"), estado)


# --------------------------------------------------------------------------- rutas citadas


def _candidate(token: str) -> str | None:
    """La ruta que un texto entre comillas invertidas parece citar, o None si no es una ruta."""
    t = token.strip()
    if not t or re.search(r"\s", t):
        return None
    if t.startswith(("http://", "https://", "/", "-", "~", "<")):
        return None
    if any(c in t for c in "*?<>{}$=|\\"):
        return None
    t = t.split("#", 1)[0]
    t = re.sub(r":\d+$", "", t)
    if not t or ":" in t:
        return None
    if "/" in t or t.lower().endswith(KNOWN_EXTENSIONS):
        return t
    return None


def check_paths(root: Path) -> Check:
    faltan: list[str] = []
    vistas: set[str] = set()
    for documento in ("README.md", "DECISIONES.md", "docs/VIDEO.md"):
        texto = _read(root, documento)
        if texto is None:
            continue
        for token in re.findall(r"`([^`\n]+)`", texto):
            ruta = _candidate(token)
            if ruta is None:
                continue
            ruta = ruta.rstrip("/")
            if ruta and ruta not in vistas and not (root / ruta).exists():
                vistas.add(ruta)
                faltan.append(f"{ruta} (citada en {documento})")
    if faltan:
        return Check(CHECK_PATHS, False, "no existen: " + _listed(faltan))
    return Check(CHECK_PATHS, True, "todas las rutas citadas existen")


# --------------------------------------------------------------------------- DECISIONES.md


def word_count(text: str) -> int:
    """Palabras de un documento, sin bloques de código, separadores de tabla ni sintaxis."""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    lineas = [
        x for x in text.splitlines() if not (re.fullmatch(r"\s*\|?[\s:|-]+\|?\s*", x) and "-" in x)
    ]
    limpio = re.sub(r"[|*#>`]", " ", "\n".join(lineas))
    return sum(1 for palabra in limpio.split() if re.search(r"\w", palabra))


def check_decisiones_table(root: Path) -> Check:
    texto = _read(root, "DECISIONES.md")
    if texto is None:
        return Check(CHECK_DECISIONES_TABLE, False, "falta DECISIONES.md en la raíz")
    filas: dict[int, list[list[str]]] = {}
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea.startswith("|"):
            continue
        celdas = [c.strip() for c in linea.strip("|").split("|")]
        if celdas and celdas[0].isdigit():
            filas.setdefault(int(celdas[0]), []).append(celdas)
    problemas = []
    if faltan := [n for n in range(1, NEEDS + 1) if n not in filas]:
        problemas.append("faltan las filas " + ", ".join(map(str, faltan)))
    if repetidas := [n for n, v in sorted(filas.items()) if len(v) > 1]:
        problemas.append("filas repetidas " + ", ".join(map(str, repetidas)))
    if fuera := [n for n in sorted(filas) if not 1 <= n <= NEEDS]:
        problemas.append(f"filas fuera del 1 al {NEEDS}: " + ", ".join(map(str, fuera)))
    incompletas = [
        n
        for n, v in sorted(filas.items())
        if len(v[0]) < 5 or any(not celda for celda in v[0][1:5])
    ]
    if incompletas:
        problemas.append(
            "celdas vacías o columnas de menos en la fila " + ", ".join(map(str, incompletas))
        )
    if problemas:
        return Check(CHECK_DECISIONES_TABLE, False, "; ".join(problemas))
    return Check(
        CHECK_DECISIONES_TABLE, True, f"las {NEEDS} necesidades, cada una con sus cinco columnas"
    )


def check_decisiones_length(root: Path) -> Check:
    texto = _read(root, "DECISIONES.md")
    if texto is None:
        return Check(CHECK_DECISIONES_LENGTH, False, "falta DECISIONES.md en la raíz")
    palabras = word_count(texto)
    return Check(
        CHECK_DECISIONES_LENGTH, palabras <= MAX_WORDS, f"{palabras} palabras (máximo {MAX_WORDS})"
    )


# --------------------------------------------------------------------------- conjunto


_CHECKS = (
    check_readme,
    check_readme_links,
    check_video_state,
    check_paths,
    check_decisiones_table,
    check_decisiones_length,
)


def check_all(root: Path | str) -> list[Check]:
    return [comprobar(Path(root)) for comprobar in _CHECKS]


def main(argv: list[str] | None = None) -> int:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Verifica README, DECISIONES.md y el guion del video"
    )
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--json", action="store_true", help="salida legible por máquina")
    args = parser.parse_args(argv)

    resultados = check_all(args.root)
    ok = all(c.ok for c in resultados)
    if args.json:
        carga = {
            "ok": ok,
            "checks": [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in resultados],
        }
        print(json.dumps(carga, ensure_ascii=False))
    else:
        for c in resultados:
            print(f"{'OK   ' if c.ok else 'FALLA'} {c.name}: {c.detail}")
        print("Documentos en orden." if ok else "Hay documentos que corregir.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
