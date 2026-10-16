"""Utilidades compartidas por los hooks de proyecto (solo biblioteca estándar).

Contrato de salida de un hook: código 0 permite; código 2 con el motivo por stderr bloquea. Los
hooks de bloqueo capturan sus propios errores y salen con 2 (fallan cerrado): cualquier otro código
distinto de 0 y 2 no bloquearía.
"""

from __future__ import annotations

import functools
import json
import os
import posixpath
import re
import shlex
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, TextIO

# Código de producción = todo `.py` salvo los que cuelgan de estos directorios. Criterio por
# exclusión: un directorio de código nuevo queda protegido sin tocar esta configuración.
EXCLUDED_DIRS = frozenset({"tests", "scripts", ".claude", ".specify", ".venv", "docs", "specs"})
REQUIRED_ARTIFACTS = ("spec.md", "plan.md", "tasks.md")

_ABSOLUTE = re.compile(r"^(?:[A-Za-z]:/|/)")


# --------------------------------------------------------------------------- entrada


def read_payload(stream: TextIO | None = None) -> dict[str, Any]:
    text = (stream or sys.stdin).read()
    if not text.strip():
        raise ValueError("la entrada del hook está vacía")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"la entrada del hook no es JSON válido: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("la entrada del hook debe ser un objeto JSON")
    return data


def project_root(payload: dict[str, Any] | None = None) -> str:
    return os.environ.get("CLAUDE_PROJECT_DIR") or (payload or {}).get("cwd") or os.getcwd()


# --------------------------------------------------------------------------- rutas


def relative_path(path: str, root: str) -> str:
    """Ruta POSIX relativa a `root`; si queda fuera del proyecto, se devuelve absoluta."""
    root_posix = posixpath.normpath(root.replace("\\", "/"))
    raw = path.replace("\\", "/")
    joined = raw if _ABSOLUTE.match(raw) else posixpath.join(root_posix, raw)
    normalized = posixpath.normpath(joined)
    if normalized.lower() == root_posix.lower():
        return ""
    if normalized.lower().startswith(root_posix.lower() + "/"):
        return normalized[len(root_posix) + 1 :]
    return normalized


def is_production_path(rel: str) -> bool:
    """¿Es código de producción? `rel` es la ruta relativa en formato POSIX."""
    lowered = rel.replace("\\", "/").lower()
    if _ABSOLUTE.match(lowered):  # fuera del proyecto: no es del repositorio
        return False
    if not lowered.endswith(".py"):
        return False
    return not any(part in EXCLUDED_DIRS for part in lowered.split("/")[:-1])


# --------------------------------------------------------------------------- terminal

_SEPARATORS = {"|", ";", "&&", "||", "&"}
_COPY_VERBS = {"cp", "mv", "copy", "move", "copy-item", "move-item", "xcopy"}
_PS_WRITERS = {"set-content", "add-content", "out-file"}
_GLUED_REDIRECT = re.compile(r"""(?<=\S)(?<![<>\-=])\d?>{1,2}(?![=&])\s*["']?([^\s&|;<>()"']+)""")
_PY_OPEN_WRITE = re.compile(r"""open\(\s*['"]([^'"]+)['"]\s*,\s*['"][^'"]*[wax+][^'"]*['"]""")
_PY_PATH_WRITE = re.compile(r"""Path\(\s*['"]([^'"]+)['"]\s*\)\.write_(?:text|bytes)""")


def _tokens(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=False)
    except ValueError:
        return command.split()


def _unquote(token: str) -> str:
    return token.strip().strip("'\"")


def bash_write_targets(command: str) -> list[str]:
    """Rutas hacia las que una orden de terminal escribe (heurística sobre el texto de la orden).

    Cubre redirecciones, `tee`, `Set-Content`/`Add-Content`/`Out-File`, `sed -i`, `cp`/`mv` (solo el
    destino) y `python` que abre un archivo para escribir. Una orden que construya el nombre del
    archivo en tiempo de ejecución puede eludirla: es un límite conocido.
    """
    tokens = _tokens(command)
    lowered = [t.lower() for t in tokens]
    targets: list[str] = []

    for index, token in enumerate(tokens):
        redirect = re.fullmatch(r"\d?>{1,2}(.*)", token)
        if redirect:
            rest = redirect.group(1)
            if rest and not rest.startswith("&"):
                targets.append(_unquote(rest))
            elif not rest and index + 1 < len(tokens):
                targets.append(_unquote(tokens[index + 1]))
            continue

        verb = lowered[index]
        following = []
        for other in tokens[index + 1 :]:
            if other in _SEPARATORS:
                break
            following.append(other)

        if verb == "tee":
            targets += [_unquote(t) for t in following if not t.startswith("-")]
        elif verb in _PS_WRITERS:
            targets += [_unquote(t) for t in following if _unquote(t).lower().endswith(".py")]
        elif verb == "sed" and any(t.startswith("-i") or t == "--in-place" for t in following):
            targets += [_unquote(t) for t in following if _unquote(t).lower().endswith(".py")]
        elif verb in _COPY_VERBS:
            positional = [t for t in following if not t.startswith("-")]
            if len(positional) >= 2:
                targets.append(_unquote(positional[-1]))

    targets += _GLUED_REDIRECT.findall(command)  # `echo x>ruta.py`, `echo x>"ruta.py"`
    targets += _PY_OPEN_WRITE.findall(command)
    targets += _PY_PATH_WRITE.findall(command)

    seen: set[str] = set()
    ordered = []
    for target in targets:
        if target and target not in seen:
            seen.add(target)
            ordered.append(target)
    return ordered


# --------------------------------------------------------------------------- feature activa


def current_branch(root: str) -> str | None:
    for args in (["symbolic-ref", "--short", "HEAD"], ["rev-parse", "--abbrev-ref", "HEAD"]):
        try:
            proc = subprocess.run(
                ["git", *args], cwd=root, capture_output=True, text=True, timeout=10, check=False
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    return None


def active_feature(root: str, branch: str | None = None) -> Path | None:
    """Carpeta `specs/NNN-*` del ticket activo, o None si no hay ticket.

    La rama manda: su prefijo numérico (`009-…`) apunta a `specs/009-*`. Solo si la rama no tiene
    número se usa el puntero `.specify/feature.json`, que no se versiona y puede estar obsoleto.
    """
    base = Path(root)
    branch = current_branch(root) if branch is None else branch
    number = re.match(r"^(\d{3})-", branch or "")
    if number:
        specs = base / "specs"
        found = [p for p in sorted(specs.glob(f"{number.group(1)}-*")) if p.is_dir()]
        return found[0] if len(found) == 1 else None
    pointer = base / ".specify" / "feature.json"
    if pointer.is_file():
        folder = json.loads(pointer.read_text(encoding="utf-8")).get("feature_directory")
        if folder and (base / folder).is_dir():
            return base / folder
    return None


def missing_artifacts(feature_dir: Path) -> list[str]:
    return [name for name in REQUIRED_ARTIFACTS if not (feature_dir / name).is_file()]


# --------------------------------------------------------------------------- bloqueo


def warn(message: str) -> None:
    """Escribe un mensaje por stderr en bytes UTF-8, sin bloquear.

    La codificación por defecto de stderr en Windows (cp1252) rompe las tildes en el mensaje que
    ve el desarrollador.
    """
    data = (message.rstrip() + "\n").encode("utf-8")
    try:
        sys.stderr.buffer.write(data)
        sys.stderr.buffer.flush()
    except AttributeError:  # un stderr sin `buffer` (p. ej. capturado por una prueba)
        sys.stderr.write(data.decode("utf-8"))


def block(message: str) -> None:
    """Bloquea la acción: motivo por stderr y código de salida 2."""
    warn(message)
    raise SystemExit(2)


def fail_closed(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Convierte cualquier error inesperado de un hook de bloqueo en un bloqueo (código 2)."""

    def decorator(function: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(function)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return function(*args, **kwargs)
            except SystemExit:
                raise
            except Exception as exc:
                block(f"El hook {name} falló y deniega por seguridad: {exc}")

        return wrapper

    return decorator


def run(name: str, handler: Callable[[dict[str, Any]], None]) -> None:
    """Punto de entrada de un hook de bloqueo: lee la entrada, ejecuta `handler`, falla cerrado."""

    @fail_closed(name)
    def main() -> None:
        handler(read_payload())

    main()
    raise SystemExit(0)
