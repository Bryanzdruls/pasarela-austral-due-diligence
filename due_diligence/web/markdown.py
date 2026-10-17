"""Analizador mínimo de Markdown: devuelve bloques de datos, nunca HTML (FR-013, FR-010).

El modelo escribe su respuesta con formato (títulos, listas, tablas, negritas). Aquí se convierte en
una estructura JSON que la página dibuja con nodos del DOM y `textContent`; por eso un `<img>` o un
enlace dentro del texto se queda como texto. Solo se reconoce lo que el coordinador usa; lo demás
se muestra tal cual. Todo está acotado: una respuesta enorme no produce una estructura enorme.
"""

import re
from typing import Any

MAX_BLOQUES = 200
MAX_ITEMS = 100
MAX_FILAS = 100

_TITULO = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_VINETA = re.compile(r"^\s*[-*•]\s+(.*\S)\s*$")
_NUMERADA = re.compile(r"^\s*\d+[.)]\s+(.*\S)\s*$")
_SEPARADOR = re.compile(r"^\s*([-*_])(?:\s*\1){2,}\s*$")
_CELDA_SEPARADORA = re.compile(r":?-+:?")
_INLINE = re.compile(r"\*\*(?=\S)([^\n]+?)(?<=\S)\*\*|`([^`\n]+)`")

Inline = list[dict[str, str]]


def _inline(texto: str) -> Inline:
    """Texto con negrita (`**x**`) y código (`x`) marcados; lo demás, texto."""
    segmentos: Inline = []
    cursor = 0
    for hallazgo in _INLINE.finditer(texto):
        if hallazgo.start() > cursor:
            segmentos.append({"t": "texto", "v": texto[cursor : hallazgo.start()]})
        if hallazgo.group(1) is not None:
            segmentos.append({"t": "negrita", "v": hallazgo.group(1)})
        else:
            segmentos.append({"t": "codigo", "v": hallazgo.group(2)})
        cursor = hallazgo.end()
    if cursor < len(texto):
        segmentos.append({"t": "texto", "v": texto[cursor:]})
    return segmentos


def _celdas(linea: str) -> list[str]:
    return [celda.strip() for celda in linea.strip().strip("|").split("|")]


def _es_fila(linea: str) -> bool:
    return linea.lstrip().startswith("|")


def _es_separadora(linea: str) -> bool:
    return _es_fila(linea) and all(_CELDA_SEPARADORA.fullmatch(c) for c in _celdas(linea))


def _tabla(lineas: list[str], i: int) -> tuple[dict[str, Any], int]:
    cabecera = [_inline(c) for c in _celdas(lineas[i])]
    filas: list[list[Inline]] = []
    j = i + 2
    while j < len(lineas) and _es_fila(lineas[j]):
        if len(filas) < MAX_FILAS:
            filas.append([_inline(c) for c in _celdas(lineas[j])])
        j += 1
    return {"t": "tabla", "cabecera": cabecera, "filas": filas}, j


def _lista(lineas: list[str], i: int, patron: re.Pattern[str]) -> tuple[dict[str, Any], int]:
    items: list[Inline] = []
    j = i
    while j < len(lineas) and (m := patron.match(lineas[j])) and not _SEPARADOR.match(lineas[j]):
        if len(items) < MAX_ITEMS:
            items.append(_inline(m.group(1)))
        j += 1
    return {"t": "lista", "ordenada": patron is _NUMERADA, "items": items}, j


def a_bloques(texto: Any) -> list[dict[str, Any]]:
    """Bloques de datos de un texto con formato Markdown; lista vacía si no hay nada que mostrar."""
    if not isinstance(texto, str) or not texto.strip():
        return []
    lineas = texto.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    bloques: list[dict[str, Any]] = []
    parrafo: list[str] = []

    def cerrar() -> None:
        if parrafo:
            bloques.append({"t": "parrafo", "inline": _inline("\n".join(parrafo))})
        parrafo.clear()

    i = 0
    while i < len(lineas) and len(bloques) < MAX_BLOQUES:
        linea = lineas[i].rstrip()
        if not linea.strip():
            cerrar()
            i += 1
        elif titulo := _TITULO.match(linea):
            cerrar()
            nivel = len(titulo.group(1))
            bloques.append({"t": "titulo", "nivel": nivel, "inline": _inline(titulo.group(2))})
            i += 1
        elif _SEPARADOR.match(linea):
            cerrar()
            bloques.append({"t": "separador"})
            i += 1
        elif _es_fila(linea) and i + 1 < len(lineas) and _es_separadora(lineas[i + 1]):
            cerrar()
            bloque, i = _tabla(lineas, i)
            bloques.append(bloque)
        elif _VINETA.match(linea) or _NUMERADA.match(linea):
            cerrar()
            patron = _VINETA if _VINETA.match(linea) else _NUMERADA
            bloque, i = _lista(lineas, i, patron)
            bloques.append(bloque)
        else:
            parrafo.append(linea.strip())
            i += 1
    cerrar()
    return bloques[:MAX_BLOQUES]  # un párrafo pendiente puede pasarse por uno del tope
