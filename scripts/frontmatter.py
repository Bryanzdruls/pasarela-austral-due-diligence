"""Lector mínimo del frontmatter de reglas, agentes y skills (solo biblioteca estándar).

Soporta lo que usan los archivos de este repositorio: valores simples, listas en bloque (`- x`) y
listas en línea (`[a, b]`). No pretende ser un lector de YAML completo.
"""

from __future__ import annotations

import re
from typing import Any

_KEY = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")
_ITEM = re.compile(r"^\s+-\s+(.*)$")


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Frontmatter de un archivo Markdown como diccionario; vacío si no tiene o no está cerrado."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}

    data: dict[str, Any] = {}
    key: str | None = None
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = _ITEM.match(line)
        if item and key is not None and isinstance(data.get(key), list):
            data[key].append(_unquote(item.group(1)))
            continue
        match = _KEY.match(line)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        if value == "":
            data[key] = []
        elif value.startswith("[") and value.endswith("]"):
            data[key] = [_unquote(part) for part in value[1:-1].split(",") if part.strip()]
        else:
            data[key] = _unquote(value)
    return data


def as_list(value: Any) -> list[str]:
    """Valor de frontmatter como lista: separa por comas o espacios fuera de paréntesis."""
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    items: list[str] = []
    current: list[str] = []
    depth = 0
    for char in str(value):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if depth == 0 and (char == "," or char.isspace()):
            if current:
                items.append("".join(current))
                current = []
            continue
        current.append(char)
    if current:
        items.append("".join(current))
    return items
