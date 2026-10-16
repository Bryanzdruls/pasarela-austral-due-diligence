"""Hook PreToolUse (Read|Edit|Write|Bash): los secretos y las variables de entorno no se tocan.

Bloquea leer o modificar archivos de secretos (`.env`, `.env.*`, `secrets/`, `*.pem`, `*.key`,
`credentials*.json`, `id_rsa*`). La plantilla `.env.example` sí está permitida. Es una segunda capa
sobre `permissions.deny`: `deny` no cubre subprocesos que abren el archivo por su cuenta; aquí se
revisa además el texto de las órdenes de terminal. Una orden que construya el nombre del archivo en
tiempo de ejecución puede eludir la inspección del texto (límite conocido).
"""

import re
from typing import Any

import common

_TEMPLATE_NAMES = frozenset({".env.example"})
_SAFE_COMMANDS = frozenset({"ls", "dir", "test-path", "stat"})  # solo nombran el archivo
_SPLIT = re.compile(r"""[\s'"(),;|&<>=]+""")

# Órdenes cuyo texto es un mensaje, no código que se ejecute: el mensaje de un commit o el cuerpo de
# un pull request puede mencionar `.env` sin tocarlo. No se aplica a `python`, `cat`, etc.: un
# heredoc de código sí se ejecuta y podría leer el archivo.
_MESSAGE_COMMAND = r"\b(?:git\s+(?:commit|tag)|gh\s+(?:pr|issue|release))\b"
_HEREDOC_BODY = re.compile(
    r"(?P<intro>" + _MESSAGE_COMMAND + r"[^\n]*?<<-?\s*(?P<q>['\"]?)(?P<tag>\w+)(?P=q)[^\n]*)"
    r"\n.*?\n(?P=tag)(?=\s|$)",
    re.DOTALL,
)
_MESSAGE_ARGUMENT = re.compile(
    r"""(?P<flag>(?<!\w)(?:-m|--message|--body|--title|--notes))(?:=|\s+)(?:"[^"]*"|'[^']*')"""
)


def without_messages(command: str) -> str:
    """Quita de una orden de commit o de pull request el texto del mensaje (no se ejecuta)."""
    if not re.search(_MESSAGE_COMMAND, command):
        return command
    command = _HEREDOC_BODY.sub(lambda match: match.group("intro"), command)
    return _MESSAGE_ARGUMENT.sub(lambda match: match.group("flag"), command)


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
    if "secrets" in parts[:-1]:
        return True
    if name.endswith((".pem", ".key")):
        return True
    return bool(re.fullmatch(r"credentials.*\.json", name) or name.startswith("id_rsa"))


def referenced_secrets(command: str) -> list[str]:
    candidates = [part for part in _SPLIT.split(command) if part]
    return [part for part in candidates if is_protected(part)]


def _first_word(command: str) -> str:
    words = command.strip().split()
    return words[0].lower() if words else ""


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
    elif tool == "Bash":
        command = without_messages(tool_input.get("command") or "")
        if _first_word(command) not in _SAFE_COMMANDS:
            offenders = referenced_secrets(command)

    if offenders:
        name = offenders[0].replace("\\", "/").split("/")[-1]
        common.block(
            "Los archivos de secretos y de variables de entorno no se leen ni se modifican "
            f"desde Claude Code: {name}. La plantilla .env.example sí está permitida."
        )


if __name__ == "__main__":
    common.run("secrets_guard", handle)
