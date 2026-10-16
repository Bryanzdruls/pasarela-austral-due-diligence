"""Hook PreToolUse (Edit|Write|Bash): no se escribe código de producción sin su especificación.

Bloquea escribir código de producción —con las herramientas de edición o con una orden de terminal
que escriba un archivo— si el ticket activo no tiene `spec.md`, `plan.md` y `tasks.md` en `specs/`.
El ticket activo sale del prefijo numérico de la rama (con respaldo en `.specify/feature.json`).
"""

from typing import Any

import common

_COMMAND_FOR = {"spec.md": "specify", "plan.md": "plan", "tasks.md": "tasks"}


def _targets(payload: dict[str, Any]) -> list[str]:
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input") or {}
    if tool in ("Edit", "Write"):
        path = tool_input.get("file_path")
        return [path] if path else []
    if tool == "Bash":
        return common.bash_write_targets(tool_input.get("command") or "")
    return []


def handle(payload: dict[str, Any]) -> None:
    root = common.project_root(payload)
    production = [
        rel
        for target in _targets(payload)
        if common.is_production_path(rel := common.relative_path(target, root))
    ]
    if not production:
        return

    feature = common.active_feature(root)
    if feature is None:
        common.block(
            "La rama no corresponde a un ticket (NNN-…): no hay especificación activa. "
            "Crea la rama del ticket y ejecuta /speckit-specify antes de escribir código "
            f"({production[0]})."
        )
    missing = common.missing_artifacts(feature)
    if missing:
        steps = ", ".join(f"/speckit-{_COMMAND_FOR[name]}" for name in missing)
        common.block(
            f"Falta {', '.join(missing)} en specs/{feature.name}/. "
            f"Ejecuta {steps} antes de escribir código ({production[0]})."
        )


if __name__ == "__main__":
    common.run("spec_gate", handle)
