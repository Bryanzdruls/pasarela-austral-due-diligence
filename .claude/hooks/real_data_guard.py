"""Hook PreToolUse (Edit|Write|Bash): ningún archivo con forma de dato real.

Bloquea escribir contenido con forma de número de tarjeta, de NIT o de documento de identidad
reales (constitución, principio II). Los identificadores ficticios (`FICT-NNNN`, `CO-XX-NNNN`) y el
texto corriente no se tocan. En `Bash` revisa el texto de la orden, para que `echo <valor> > f` no
esquive la comprobación; una orden que construya el valor en tiempo de ejecución puede eludirla.
"""

import re
from typing import Any

import common

# Tarjeta: 13 a 19 dígitos aislados (no pegados a letras: hashes y sumas de verificación),
# contiguos o en grupos de cuatro, que además pasen la comprobación de Luhn.
_ISOLATED_START = r"(?<![A-Za-z0-9_])"
_ISOLATED_END = r"(?![A-Za-z0-9_])"
_CARD_CONTIGUOUS = re.compile(_ISOLATED_START + r"\d{13,19}" + _ISOLATED_END)
_CARD_GROUPED = (
    re.compile(_ISOLATED_START + r"\d{4}([ -])\d{4}\1\d{4}\1\d{1,4}(?:\1\d{1,3})?" + _ISOLATED_END),
    re.compile(_ISOLATED_START + r"\d{4}([ -])\d{6}\1\d{5}" + _ISOLATED_END),  # 4-6-5
)
# NIT: NNN.NNN.NNN-D o NNNNNNNNN-D.
_NIT = re.compile(r"(?<![\w.-])(?:\d{3}\.\d{3}\.\d{3}-\d|\d{9}-\d)(?!\w)")
# Documento: etiqueta + 6 a 10 dígitos. Sin etiqueta no se bloquea (marcas de tiempo, sumas).
_DOCUMENT = re.compile(
    r"(?<![\w/.-])(?:c[eé]dula|cc|nit|documento|identificaci[oó]n)\b[\W_]{0,12}?(\d{6,10})(?!\w)",
    re.IGNORECASE,
)


def luhn_valid(digits: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def find_sensitive(text: str) -> list[tuple[str, str]]:
    """Valores con forma de dato real en `text`, como pares (tipo, valor), sin repetidos."""
    found: list[tuple[str, str]] = []

    def add(kind: str, value: str) -> None:
        if (kind, value) not in found:
            found.append((kind, value))

    for match in _CARD_CONTIGUOUS.finditer(text):
        if luhn_valid(match.group(0)):
            add("tarjeta", match.group(0))
    for pattern in _CARD_GROUPED:
        for match in pattern.finditer(text):
            digits = re.sub(r"\D", "", match.group(0))
            if 13 <= len(digits) <= 19 and luhn_valid(digits):
                add("tarjeta", match.group(0))
    for match in _NIT.finditer(text):
        add("NIT", match.group(0))
    for match in _DOCUMENT.finditer(text):
        add("documento", match.group(1))
    return found


def mask(value: str, keep: int = 2) -> str:
    """Oculta todos los dígitos salvo los últimos `keep`, conservando los separadores."""
    total = sum(char.isdigit() for char in value)
    seen = 0
    out = []
    for char in value:
        if char.isdigit():
            seen += 1
            out.append(char if seen > total - keep else "*")
        else:
            out.append(char)
    return "".join(out)


def _text(payload: dict[str, Any]) -> str:
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input") or {}
    if tool == "Write":
        return tool_input.get("content") or ""
    if tool == "Edit":
        return tool_input.get("new_string") or ""
    if tool in ("Bash", "PowerShell"):
        return tool_input.get("command") or ""
    return ""


def handle(payload: dict[str, Any]) -> None:
    findings = find_sensitive(_text(payload))
    if not findings:
        return
    kind, value = findings[0]
    extra = f" (y {len(findings) - 1} más)" if len(findings) > 1 else ""
    common.block(
        f"Contenido con forma de {kind} reales: {mask(value)}{extra}. "
        "Usa un identificador ficticio (FICT-NNNN)."
    )


if __name__ == "__main__":
    common.run("real_data_guard", handle)
