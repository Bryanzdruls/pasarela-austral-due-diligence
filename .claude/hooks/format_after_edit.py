"""Hook PostToolUse (Edit|Write): el código queda formateado después de cada edición.

Solo formatea archivos `.py`. Busca el formateador en este orden: `ruff` en el PATH, `uv run ruff`
y `python -m uv run ruff`. Nunca bloquea: si no hay formateador o falla, avisa por stderr y sale con
código 0, para no perder una edición ya hecha.
"""

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from typing import Any

import common


def candidates(which: Callable[[str], Any] = shutil.which) -> list[list[str]]:
    """Órdenes de formateo en orden de preferencia."""
    commands: list[list[str]] = []
    if which("ruff"):
        commands.append(["ruff", "format"])
    if which("uv"):
        commands.append(["uv", "run", "ruff", "format"])
    commands.append([sys.executable, "-m", "uv", "run", "ruff", "format"])
    return commands


def format_file(
    path: str,
    root: str,
    which: Callable[[str], Any] = shutil.which,
    run: Callable[..., Any] = subprocess.run,
) -> str | None:
    """Formatea `path`; devuelve un aviso si no se pudo y None si quedó formateado."""
    failure: str | None = None
    for command in candidates(which):
        try:
            result = run(
                [*command, path], cwd=root, capture_output=True, text=True, timeout=25, check=False
            )
        except (OSError, subprocess.SubprocessError):
            continue  # este formateador no está o no responde: se prueba el siguiente
        if result.returncode == 0:
            return None
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        failure = (
            f"Aviso: no se pudo dar formato a {path}: {detail[0] if detail else 'sin detalle'}"
        )
        break  # el formateador existe pero rechazó el archivo: otro daría el mismo resultado
    return failure or f"Aviso: no hay un formateador disponible (ruff o uv) para {path}."


def handle(payload: dict[str, Any]) -> None:
    tool_input = payload.get("tool_input") or {}
    raw = tool_input.get("file_path") or ""
    if not raw.lower().endswith(".py"):
        return
    root = common.project_root(payload)
    path = os.path.normpath(os.path.join(root, raw.replace("\\", "/")))
    if not os.path.isfile(path):
        return
    warning = format_file(path, root)
    if warning:
        common.warn(warning)


def main() -> None:
    try:
        handle(common.read_payload())
    except Exception as exc:  # un hook posterior a la edición nunca debe bloquear
        common.warn(f"Aviso: el hook de formateo no pudo ejecutarse: {exc}")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
