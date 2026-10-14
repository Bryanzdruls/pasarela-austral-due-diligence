import json
import re

from mcp_server import store
from mcp_server.tools import informes, listas, noticias, registro, riesgo

FICTICIO = re.compile(r"^FICT-\d{4}$")
ID_COMERCIO = re.compile(r"^CO-[A-Z]{2}-\d{4}$")
SOURCE_NAME = re.compile(r"_fictici[oa]s?$")
# Cualquier cadena con 13 a 19 dígitos (con espacios o guiones) parece una tarjeta.
CARD_LIKE = re.compile(r"(?:\d[ -]?){13,19}")
LONG_NUMBER = re.compile(r"\d{7,}")


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


def test_identifiers_follow_the_fictitious_formats():
    for c in store.load("comercios"):
        assert ID_COMERCIO.match(c["id"]), c["id"]
        assert FICTICIO.match(c["nit"]), c["nit"]
    for p in store.load("personas"):
        assert FICTICIO.match(p["documento"]), p["documento"]


def test_every_source_name_is_marked_fictitious():
    names = {registro.SOURCE, listas.SOURCE, noticias.SOURCE, riesgo.SOURCE, informes.SOURCE}
    for c in store.load("comercios"):
        names |= {f["source"] for f in c["fuentes_registro"]}
    names |= {n["fuente"] for n in store.load("noticias")}
    for name in names:
        assert SOURCE_NAME.search(name), name


def test_no_value_looks_like_a_real_document_or_card():
    for file in sorted(store.DATA_DIR.glob("*.json")):
        data = json.loads(file.read_text(encoding="utf-8"))
        for text in _strings(data):
            assert not CARD_LIKE.search(text), f"{file.name}: {text}"
            assert not LONG_NUMBER.search(text), f"{file.name}: {text}"
