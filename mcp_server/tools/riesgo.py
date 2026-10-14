"""consultar_riesgo_categoria: nivel de riesgo de una categoría de negocio."""

from typing import Any

from mcp_server import faults, store
from mcp_server.envelope import error, ok

SOURCE = "catalogo_riesgo_ficticio"

DESCRIPTION = (
    "Devuelve el nivel de riesgo de una categoría de negocio. Alto riesgo: apuestas, "
    "criptoactivos, suplementos dietarios y venta de medicamentos. Si el resultado es "
    "sin_clasificar no asumas un nivel; indícalo en el informe."
)


def consultar_riesgo_categoria(categoria: str) -> dict[str, Any]:
    if (fault := faults.check("riesgo", SOURCE)) is not None:
        return fault

    try:
        text = store.require_text(categoria)
    except ValueError as exc:
        return error(SOURCE, "invalid_input", False, {"mensaje": str(exc)})

    wanted = store.normalize(text)
    nivel = next(
        (c["riesgo"] for c in store.load("categorias") if store.normalize(c["nombre"]) == wanted),
        "sin_clasificar",
    )
    return ok({"categoria": text, "riesgo": nivel}, SOURCE)
