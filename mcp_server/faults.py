"""Inyección de fallas por fuente mediante PASARELA_FAULTS (se lee en cada llamada).

Formato: lista separada por comas de fuentes (registro, listas, noticias, riesgo).
Una fuente puede llevar el sufijo ':no_reintentable' (p. ej. 'noticias:no_reintentable').
"""

import os
from typing import Any

from mcp_server.envelope import error


def _active() -> dict[str, bool]:
    """Devuelve {fuente: reintentable} para las fuentes con falla configurada."""
    raw = os.environ.get("PASARELA_FAULTS", "")
    faults: dict[str, bool] = {}
    for item in raw.split(","):
        name, _, mode = item.strip().partition(":")
        if name:
            faults[name] = mode != "no_reintentable"
    return faults


def check(fuente: str, source_name: str) -> dict[str, Any] | None:
    """Devuelve un error estructurado si la fuente tiene una falla configurada."""
    faults = _active()
    if fuente not in faults:
        return None
    return error(source_name, "source_unavailable", retryable=faults[fuente])
