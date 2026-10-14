"""consultar_registro_mercantil: identifica al comercio por nombre o identificador."""

from typing import Any

from mcp_server import faults, store
from mcp_server.envelope import error, ok

SOURCE = "registro_mercantil_ficticio"

DESCRIPTION = (
    "Busca un comercio en el registro mercantil por nombre o identificador. "
    "Úsala primero: es la única forma de identificar al comercio. "
    "Si devuelve varias coincidencias (ambiguous=true) NO elijas una: pide al analista "
    "el identificador. Si no devuelve ninguna, informa que el comercio no existe en el "
    "registro. Si las fuentes del registro reportan fechas de constitución distintas, "
    "muestra todas con su origen; no elijas una."
)


def _matches(query: str, comercio: dict[str, Any]) -> bool:
    if query.upper() == comercio["id"].upper():
        return True
    return store.name_matches(query, comercio["razon_social"])


def _describe(comercio: dict[str, Any], personas: dict[str, dict[str, Any]]) -> dict[str, Any]:
    fechas = {f["fecha_constitucion"] for f in comercio["fuentes_registro"]}
    return {
        "id": comercio["id"],
        "razon_social": comercio["razon_social"],
        "nit": comercio["nit"],
        "existe": True,
        "estado": comercio["estado"],
        "representante_legal": personas[comercio["representante_legal_id"]],
        "categoria": comercio["categoria"],
        "volumen_mensual_estimado": comercio["volumen_mensual_estimado"],
        "fuentes_registro": comercio["fuentes_registro"],
        "conflicts": ["fecha_constitucion"] if len(fechas) > 1 else [],
    }


def consultar_registro_mercantil(consulta: str) -> dict[str, Any]:
    if (fault := faults.check("registro", SOURCE)) is not None:
        return fault

    try:
        query = store.require_text(consulta)
        if not store.normalize(query):
            raise ValueError("la consulta solo contiene un sufijo societario")
    except ValueError as exc:
        return error(SOURCE, "invalid_input", False, {"mensaje": str(exc)})

    personas = {p["id"]: p for p in store.load("personas")}
    found = [_describe(c, personas) for c in store.load("comercios") if _matches(query, c)]
    return ok(
        {"match_count": len(found), "ambiguous": len(found) > 1, "matches": found},
        SOURCE,
    )
