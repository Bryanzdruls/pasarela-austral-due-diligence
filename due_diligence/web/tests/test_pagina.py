"""La página del chat: todo el texto externo entra como texto, nunca como marcado."""

import re
from pathlib import Path

PAGINA = Path(__file__).parent.parent / "static" / "index.html"
TIPOS = (
    "analista",
    "coordinador",
    "delegacion",
    "resultado",
    "hallazgo",
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


def test_the_page_draws_the_formatted_blocks_with_dom_nodes_and_text():
    html = contenido()
    assert "extra.bloques" in html or "e.extra.bloques" in html
    for bloque in ("parrafo", "titulo", "lista", "tabla", "separador"):
        assert re.search(rf"['\"]{bloque}['\"]", html), bloque
    for inline, etiqueta in (("negrita", "strong"), ("codigo", "code")):
        assert re.search(rf"['\"]{inline}['\"]", html), inline
        assert f'createElement("{etiqueta}")' in html, etiqueta
    assert "document.createElement(etiqueta)" in html  # el ayudante `hijo` crea cada nodo
    for etiqueta in ("table", "thead", "tbody", "tr", "th", "td", "ul", "ol", "li", "hr", "p"):
        assert re.search(rf'[(,?:]\s*"{etiqueta}"\s*[,):]', html), etiqueta
    assert "textContent" in html and "innerHTML" not in html


def test_a_card_without_blocks_still_shows_its_plain_detail():
    html = contenido()
    assert "de.textContent = e.detalle" in html  # el respaldo de antes, para texto sin formato


def test_the_page_defines_the_finding_card():
    html = contenido()
    assert re.search(r"hallazgo\s*:\s*['\"]Hallazgo['\"]", html)
    assert "--hallazgo" in html and ".hallazgo" in html


def test_the_message_box_is_pinned_to_the_bottom_even_when_the_chat_is_empty():
    html = contenido()
    assert "min-height: 100dvh" in html or "min-height: 100vh" in html
    assert re.search(r"main\s*\{[^}]*flex:\s*1", html)
    assert "min-height: 40vh" not in html  # lo que dejaba flotar el formulario a media pantalla
    assert re.search(r"#conversacion\s*\{[^}]*flex:\s*1", html)


def test_sending_an_empty_message_warns_and_returns_the_focus():
    html = contenido()
    assert "Escribe un mensaje antes de enviar." in html
    assert re.search(r"if\s*\(!texto\)[^}]*aviso\.textContent", html, re.DOTALL)
    assert "campo.focus()" in html


def test_the_warning_goes_away_when_the_analyst_types():
    html = contenido()
    assert re.search(r"campo\.addEventListener\(\s*[\"']input[\"']", html)


def test_the_page_loads_nothing_from_outside():
    html = contenido()
    assert not re.search(r"(?:src|href)=[\"']https?://", html)
    assert "<script src" not in html
