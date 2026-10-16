"""Hook PreToolUse reutilizable: nada con forma de dato real en lo que se escribe.

Bloquea escribir contenido con forma de número de tarjeta, de NIT o de documento de identidad
reales. Los identificadores ficticios (`FICT-NNNN`, `CO-XX-NNNN`) y el texto corriente no se tocan.
En `Bash` y `PowerShell` revisa el texto de la orden, para que `echo <valor> > f` no esquive la
comprobación; una orden que construya el valor en tiempo de ejecución puede eludirla.

Es una barrera contra descuidos del asistente, no contra ofuscación deliberada. Solo biblioteca
estándar: no depende de nada del repositorio donde se instale.
"""

import json
import re
import sys

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


def luhn_valid(digits):
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def find_sensitive(text):
    """Valores con forma de dato real en `text`, como pares (tipo, valor), sin repetidos."""
    found = []

    def add(kind, value):
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


def mask(value, keep=2):
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


def _text(payload):
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        raise ValueError("tool_input debe ser un objeto")
    key = {
        "Write": "content",
        "Edit": "new_string",
        "Bash": "command",
        "PowerShell": "command",
    }.get(tool)
    if key is None:
        return ""
    value = tool_input.get(key) or ""
    if not isinstance(value, str):
        raise ValueError(f"{key} debe ser texto")
    return value


def _stderr(message):
    sys.stderr.buffer.write((message + "\n").encode("utf-8"))
    sys.stderr.buffer.flush()


def main():
    try:
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            raise ValueError("el payload debe ser un objeto JSON")
        findings = find_sensitive(_text(payload))
    except Exception as exc:  # un hook que bloquea falla cerrado: ante la duda, deniega
        _stderr(f"El hook real_data_guard falló y deniega por seguridad: {exc}")
        sys.exit(2)

    if findings:
        kind, value = findings[0]
        extra = f" (y {len(findings) - 1} más)" if len(findings) > 1 else ""
        _stderr(
            f"Contenido con forma de {kind} reales: {mask(value)}{extra}. "
            "Usa un identificador ficticio (FICT-NNNN)."
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
