"""La página del chat: todo el texto externo entra como texto, nunca como marcado."""

import re
from pathlib import Path

PAGINA = Path(__file__).parent.parent / "static" / "index.html"
TIPOS = (
    "analista",
    "coordinador",
    "delegacion",
    "resultado",
    "bloqueo",
    "informe",
    "escalamiento",
    "fin",
    "error",
)


def contenido():
    return PAGINA.read_text(encoding="utf-8")


def test_the_page_never_inserts_markup_or_evaluates_code():
    html = contenido()
    for prohibido in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
        assert prohibido not in html, prohibido
    assert "new Function" not in html
    assert "textContent" in html


def test_the_page_opens_the_event_stream_and_posts_messages_to_the_contract_routes():
    html = contenido()
    assert "EventSource" in html
    assert "/api/conversaciones" in html and "/mensajes" in html and "/eventos" in html


def test_the_page_defines_every_event_type_of_the_contract():
    html = contenido()
    for tipo in TIPOS:
        assert re.search(rf"\b{tipo}\b", html), tipo


def test_the_page_loads_nothing_from_outside():
    html = contenido()
    assert not re.search(r"(?:src|href)=[\"']https?://", html)
    assert "<script src" not in html
