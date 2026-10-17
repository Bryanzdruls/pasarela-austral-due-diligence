"""registrar_informe y escalar_a_cumplimiento: guardan; no deciden."""

from typing import Any

from mcp_server import store
from mcp_server.envelope import error, now_iso, ok

SOURCE = "registro_informes_ficticio"

DESCRIPTION_INFORME = (
    "Registra el informe de due diligence con su recomendación. Cada frente de hallazgos debe "
    "ser un objeto con `contenido`, `fuente` y `fecha` (la de la consulta), y la fuente debe ser "
    "una que respondió. Si las fuentes dan valores distintos para un mismo dato, `conflictos` "
    "los declara todos: una lista de `dato` con sus `valores`, cada uno con `valor` y `fuente`. "
    "`cobertura` lleva un objeto por frente (registro, listas, "
    "noticias, riesgo) con `estado` (`cubierto` o `sin_cubrir`) y `motivo`; todo frente que no "
    "respondió debe constar `sin_cubrir`. Este servidor solo guarda el informe: no valida ni "
    "decide la recomendación."
)

DESCRIPTION_ESCALAR = (
    "Pasa el caso a un oficial de cumplimiento, y solo si hay un hallazgo que lo justifica. El "
    "oficial no ve la conversación: el resumen debe bastarse solo. Incluye el comercio, los "
    "`hallazgos` por frente (cada uno con su `fuente` y `fecha`, en especial el frente que "
    "motiva el escalamiento), la `cobertura` alcanzada, los `conflictos` si las fuentes se "
    "contradicen, la `causa` del escalamiento (que nombra cada motivo) y la `accion_recomendada`. "
    "Si falta algún campo o un frente no trae fuente, se rechaza indicando cuáles."
)

_INFORME_REQUIRED = ("comercio_id", "recomendacion", "hallazgos", "cobertura")
_ESCALAMIENTO_REQUIRED = ("comercio_id", "hallazgos", "cobertura", "causa", "accion_recomendada")


def _blank(value: Any) -> bool:
    return not (value.strip() if isinstance(value, str) else value)


def _validate(values: dict[str, Any], required: tuple[str, ...]) -> dict[str, Any]:
    """Devuelve el detalle de lo que falla (vacío si todo está bien)."""
    partial: dict[str, Any] = {}
    missing = [name for name in required if _blank(values.get(name))]
    if missing:
        partial["campos_faltantes"] = missing
    hallazgos = values.get("hallazgos")
    if "hallazgos" not in missing:
        if isinstance(hallazgos, dict):
            sin_fuente = [
                frente
                for frente, dato in hallazgos.items()
                if not (isinstance(dato, dict) and not _blank(dato.get("fuente")))
            ]
        else:
            sin_fuente = ["hallazgos"]
        if sin_fuente:
            partial["hallazgos_sin_fuente"] = sin_fuente
    return partial


def _clean(values: dict[str, Any]) -> dict[str, Any]:
    return {k: v.strip() if isinstance(v, str) else v for k, v in values.items()}


def registrar_informe(
    comercio_id: str | None = None,
    recomendacion: str | None = None,
    hallazgos: dict[str, Any] | None = None,
    cobertura: dict[str, Any] | None = None,
    conflictos: list[Any] | None = None,
) -> dict[str, Any]:
    values = {
        "comercio_id": comercio_id,
        "recomendacion": recomendacion,
        "hallazgos": hallazgos,
        "cobertura": cobertura,
    }
    partial = _validate(values, _INFORME_REQUIRED)
    if partial:
        return error(SOURCE, "invalid_input", False, partial)
    informe_id = store.save_record(
        "INF", {**_clean(values), "conflictos": conflictos or [], "registrado_en": now_iso()}
    )
    return ok({"informe_id": informe_id}, SOURCE)


def escalar_a_cumplimiento(
    comercio_id: str | None = None,
    hallazgos: dict[str, Any] | None = None,
    cobertura: dict[str, Any] | None = None,
    causa: str | None = None,
    accion_recomendada: str | None = None,
    conflictos: list[Any] | None = None,
) -> dict[str, Any]:
    values = {
        "comercio_id": comercio_id,
        "hallazgos": hallazgos,
        "cobertura": cobertura,
        "causa": causa,
        "accion_recomendada": accion_recomendada,
    }
    partial = _validate(values, _ESCALAMIENTO_REQUIRED)
    if partial:
        return error(SOURCE, "invalid_input", False, partial)
    escalamiento_id = store.save_record(
        "ESC", {**_clean(values), "conflictos": conflictos or [], "registrado_en": now_iso()}
    )
    return ok({"escalamiento_id": escalamiento_id}, SOURCE)
