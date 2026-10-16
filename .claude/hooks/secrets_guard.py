"""Hook PreToolUse: los secretos y las variables de entorno no se tocan.

Se aplica a Read, Edit, Write, Bash, PowerShell, Grep y Glob. Bloquea leer o modificar archivos de
secretos (`.env`, `.env.*`, `secrets/`, `*.pem`, `*.key`, `credentials*.json`, `id_rsa*`). La
plantilla `.env.example` sí está permitida. Es una segunda capa
sobre `permissions.deny`: `deny` no cubre subprocesos que abren el archivo por su cuenta; aquí se
revisa además el texto de las órdenes de terminal. Una orden que construya el nombre del archivo en
tiempo de ejecución puede eludir la inspección del texto (límite conocido). El texto de la orden
se inspecciona entero, también el de un mensaje de commit: no se intenta distinguir mensajes de
código (las podas con expresiones regulares se evadían); un mensaje que nombre un archivo de
secretos se escribe en un archivo y se pasa con `git commit -F`.
"""

import re
from typing import Any

import common

_TEMPLATE_NAMES = frozenset({".env.example"})
_SPLIT = re.compile(r"""[\s'"`$(){},;|&<>=]+""")


def is_protected(path: str) -> bool:
    """¿Es un archivo de secretos? Compara en minúsculas y sin depender del separador."""
    normalized = path.replace("\\", "/").lower().strip()
    parts = [part for part in normalized.split("/") if part]
    if not parts:
        return False
    name = parts[-1]
    if name in _TEMPLATE_NAMES:
        return False
    if name == ".env" or name == ".envrc" or name.startswith(".env."):
        return True
    if name.startswith(".env") and ("*" in name or "?" in name):  # patrón: `.env*`
        return True
    if "secrets" in parts[:-1]:
        return True
    if name.endswith((".pem", ".key")):
        return True
    return bool(re.fullmatch(r"credentials.*\.json", name) or name.startswith("id_rsa"))


def referenced_secrets(command: str) -> list[str]:
    candidates = [part for part in _SPLIT.split(command) if part]
    return [part for part in candidates if is_protected(part)]


def _variants(text: str) -> list[str]:
    """El texto tal cual y unido como lo une el shell: `.e'n'v` y `.en\\v` leen el mismo."""
    joined = re.sub(r"['\"]", "", text)
    return [text, joined, joined.replace("\\", "")]


def handle(payload: dict[str, Any]) -> None:
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        raise ValueError("tool_input debe ser un objeto")

    offenders: list[str] = []
    if tool in ("Read", "Edit", "Write"):
        path = tool_input.get("file_path")
        if path and is_protected(path):
            offenders.append(path)
    elif tool in ("Bash", "PowerShell"):
        command = tool_input.get("command") or ""
        # ninguna orden se exime, ni siquiera `ls`: puede alimentar a otra con una tubería
        for variant in _variants(command):
            offenders += referenced_secrets(variant)
    elif tool in ("Grep", "Glob"):
        for key in ("path", "glob", "pattern"):
            value = tool_input.get(key)
            if (
                isinstance(value, str)
                and value
                and (
                    is_protected(value)
                    or (key == "path" and is_protected(value.rstrip("/\\") + "/x"))
                    or (key != "pattern" and referenced_secrets(value))
                )
            ):
                offenders.append(value)

    if offenders:
        name = offenders[0].replace("\\", "/").split("/")[-1]
        common.block(
            "Los archivos de secretos y de variables de entorno no se leen ni se modifican "
            f"desde Claude Code: {name}. La plantilla .env.example sí está permitida."
        )


if __name__ == "__main__":
    common.run("secrets_guard", handle)
