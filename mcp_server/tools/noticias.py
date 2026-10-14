"""buscar_noticias: menciones de un comercio o persona en un corpus de noticias ficticias."""

from typing import Any

from mcp_server import faults, store
from mcp_server.envelope import error, ok

SOURCE = "noticias_ficticias"

DESCRIPTION = (
    "Busca menciones de un comercio o persona en el corpus de noticias, por nombre o "
    "identificador. Una mención en noticias NO es una coincidencia en listas restrictivas: "
    "reporta la noticia con su fuente y no la trates como hallazgo de listas. Para listas "
    "usa consultar_listas_restrictivas."
)


def _is_match(query: str, wanted: str, record_id: str, name: str) -> bool:
    if query.upper() == record_id.upper():
        return True
    return bool(wanted) and wanted in store.normalize(name)


def _referenced_ids(query: str) -> set[str]:
    wanted = store.normalize(query)
    ids = {
        c["id"]
        for c in store.load("comercios")
        if _is_match(query, wanted, c["id"], c["razon_social"])
    }
    ids |= {
        p["id"] for p in store.load("personas") if _is_match(query, wanted, p["id"], p["nombre"])
    }
    return ids


def buscar_noticias(consulta: str) -> dict[str, Any]:
    if (fault := faults.check("noticias", SOURCE)) is not None:
        return fault

    try:
        query = store.require_text(consulta)
    except ValueError as exc:
        return error(SOURCE, "invalid_input", False, {"mensaje": str(exc)})

    ids = _referenced_ids(query)
    menciones = [
        {k: n[k] for k in ("titular", "fecha", "fuente", "resumen")}
        for n in store.load("noticias")
        if ids & set(n["menciona"])
    ]
    return ok({"menciones": menciones}, SOURCE)
