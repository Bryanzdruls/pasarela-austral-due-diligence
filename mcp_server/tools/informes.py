"""registrar_informe y escalar_a_cumplimiento: guardan; no deciden."""

from datetime import UTC, datetime
from typing import Any

from mcp_server import store
from mcp_server.envelope import error, ok

SOURCE = "registro_informes_ficticio"

DESCRIPTION_INFORME = (
    "Registra el informe de due diligence con su recomendación. Cada afirmación debe llevar "
    "su fuente; si hay frentes sin cubrir, decláralos en cobertura. Este servidor solo "
    "guarda el informe: no valida ni decide la recomendación."
)

DESCRIPTION_ESCALAR = (
    "Pasa el caso a un oficial de cumplimiento. El oficial no ve la conversación: el resumen "
    "debe bastarse solo (comercio, hallazgos por frente con fuentes, cobertura, causa del "
    "escalamiento y acción recomendada). Si falta algún campo se rechaza indicando cuáles."
)

_ESCALAMIENTO_REQUIRED = ("comercio_id", "hallazgos", "cobertura", "causa", "accion_recomendada")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _missing(values: dict[str, Any], required: tuple[str, ...]) -> list[str]:
    return [name for name in required if not values.get(name)]


def registrar_informe(
    comercio_id: str,
    recomendacion: str,
    hallazgos: dict[str, Any],
    cobertura: dict[str, Any],
    conflictos: list[Any] | None = None,
) -> dict[str, Any]:
    values = {
        "comercio_id": comercio_id,
        "recomendacion": recomendacion,
        "hallazgos": hallazgos,
        "cobertura": cobertura,
    }
    missing = _missing(values, tuple(values))
    if missing:
        return error(SOURCE, "invalid_input", False, {"campos_faltantes": missing})
    informe_id = store.save_record(
        "INF",
        {**values, "conflictos": conflictos or [], "registrado_en": _now()},
    )
    return ok({"informe_id": informe_id}, SOURCE)


def escalar_a_cumplimiento(
    comercio_id: str | None = None,
    hallazgos: dict[str, Any] | None = None,
    cobertura: dict[str, Any] | None = None,
    causa: str | None = None,
    accion_recomendada: str | None = None,
) -> dict[str, Any]:
    values = {
        "comercio_id": comercio_id,
        "hallazgos": hallazgos,
        "cobertura": cobertura,
        "causa": causa,
        "accion_recomendada": accion_recomendada,
    }
    missing = _missing(values, _ESCALAMIENTO_REQUIRED)
    if missing:
        return error(SOURCE, "invalid_input", False, {"campos_faltantes": missing})
    escalamiento_id = store.save_record("ESC", {**values, "registrado_en": _now()})
    return ok({"escalamiento_id": escalamiento_id}, SOURCE)
