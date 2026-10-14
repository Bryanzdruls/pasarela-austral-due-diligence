"""Sobre de respuesta: contenido separado de metadatos, y error estructurado."""

from datetime import UTC, datetime
from typing import Any

ERROR_CODES = frozenset({"source_unavailable", "invalid_input"})


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def ok(content: dict[str, Any], source: str) -> dict[str, Any]:
    return {
        "ok": True,
        "content": content,
        "metadata": {
            "source": source,
            "fetched_at": now_iso(),
        },
    }


def error(
    source: str,
    error_code: str,
    retryable: bool,
    partial: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if error_code not in ERROR_CODES:
        raise ValueError(f"error_code no permitido: {error_code}")
    return {
        "ok": False,
        "source": source,
        "error_code": error_code,
        "retryable": retryable,
        "partial": partial or {},
    }
