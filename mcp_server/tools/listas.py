"""consultar_listas_restrictivas: verifica un comercio o una persona contra listas ficticias."""

from typing import Any, Literal

from mcp_server import faults, store
from mcp_server.envelope import error, ok

SOURCE = "listas_restrictivas_ficticias"

DESCRIPTION = (
    "Verifica a un comercio o a una persona (por ejemplo, el representante legal) contra las "
    "listas restrictivas. Úsala solo con un comercio ya identificado de forma unívoca en el "
    "registro mercantil. Una coincidencia aquí es la única que cuenta como coincidencia en "
    "listas restrictivas; una noticia que menciona a alguien NO lo es. Recibe el identificador "
    "del comercio o de la persona, no un nombre: un identificador desconocido se rechaza."
)

_FILES = {"comercio": "comercios", "persona": "personas"}


def consultar_listas_restrictivas(
    tipo: Literal["comercio", "persona"], referencia: str
) -> dict[str, Any]:
    if (fault := faults.check("listas", SOURCE)) is not None:
        return fault

    try:
        ref = store.require_text(referencia)
        if tipo not in _FILES:
            raise ValueError("tipo debe ser 'comercio' o 'persona'")
        known = {r["id"].upper() for r in store.load(_FILES[tipo])}
        if ref.upper() not in known:
            raise ValueError(
                f"{ref!r} no es un identificador de {tipo} conocido; usa el identificador, "
                "no el nombre"
            )
    except ValueError as exc:
        return error(SOURCE, "invalid_input", False, {"mensaje": str(exc)})

    entradas = [
        {"nombre_lista": e["nombre_lista"], "fecha_inclusion": e["fecha_inclusion"]}
        for e in store.load("listas_restrictivas")
        if e["tipo"] == tipo and e["referencia"].upper() == ref.upper()
    ]
    return ok({"match": bool(entradas), "entradas": entradas}, SOURCE)
