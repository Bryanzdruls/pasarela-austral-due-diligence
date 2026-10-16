"""Hook PreToolUse: los secretos y las variables de entorno no se tocan.

Se aplica a Read, Edit, Write, Bash, PowerShell, Grep y Glob. Bloquea leer o modificar archivos de
secretos (`.env`, `.env.*`, `secrets/`, `*.pem`, `*.key`, `credentials*.json`, `id_rsa*`). La
plantilla `.env.example` sí está permitida. Es una segunda capa
sobre `permissions.deny`: `deny` no cubre subprocesos que abren el archivo por su cuenta; aquí se
revisa además el texto de las órdenes de terminal. Una orden que construya el nombre del archivo en
tiempo de ejecución puede eludir la inspección del texto (límite conocido).
"""

import re
from typing import Any

import common

_TEMPLATE_NAMES = frozenset({".env.example"})
_SAFE_COMMANDS = frozenset({"ls", "dir", "test-path", "stat"})  # solo nombran el archivo
_SPLIT = re.compile(r"""[\s'"`$(){},;|&<>=]+""")

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


_SUBSTITUTION = re.compile(r"\$\(|`|\$\{")
_COMMAND_SEGMENTS = re.compile(r"&&|\|\||[;|&\n]")


def _drop_argument(match: re.Match[str]) -> str:
    # Entre comillas dobles el shell ejecuta `$(...)` y las comillas invertidas: se conserva.
    if '"' in match.group(0) and _SUBSTITUTION.search(match.group(0)):
        return match.group(0)
    return match.group("flag")


def _drop_heredoc(match: re.Match[str]) -> str:
    # Un heredoc sin comillas en la etiqueta también expande sustituciones.
    if not match.group("q") and _SUBSTITUTION.search(match.group(0)):
        return match.group(0)
    # El cuerpo solo se poda si `git commit`/`gh ...` abre su propio tramo de la orden y su línea no
    # encadena ni sustituye nada: en cualquier otro caso el heredoc puede ser de otra orden.
    own_segment = not _COMMAND_SEGMENTS.split(match.string[: match.start()])[-1].strip()
    if not own_segment or re.search(r"[&;|`]|\$\(", match.group("intro")):
        return match.group(0)
    # Solo la forma simple `<<TAG`: con comillas o `#` antes del `<<` puede no ser un heredoc, y con
    # `<<-` el shell recorta tabulaciones al buscar el terminador y la expresión no lo imita.
    before = match.group("intro").split("<<")[0]
    if re.search(r"[\"'#]", before) or "<<-" in match.group("intro"):
        return match.group(0)
    return match.group("intro")


def without_messages(command: str) -> str:
    """Quita de una orden de commit o de pull request el texto del mensaje (no se ejecuta)."""
    if not re.search(_MESSAGE_COMMAND, command):
        return command
    command = _HEREDOC_BODY.sub(_drop_heredoc, command)
    return _MESSAGE_ARGUMENT.sub(_drop_argument, command)


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
    elif tool in ("Bash", "PowerShell"):
        command = without_messages(tool_input.get("command") or "")
        for segment in _COMMAND_SEGMENTS.split(command):
            # cada tramo se juzga por separado y una sustitución de comandos nunca es "segura"
            if (
                _first_word(segment) not in _SAFE_COMMANDS
                or _SUBSTITUTION.search(segment)
                or ">" in segment
            ):
                offenders += referenced_secrets(segment)
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
