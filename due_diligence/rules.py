"""Reglas de negocio 1 a 3 de la pasarela: lógica pura, sin SDK (ticket #3).

Las decisiones salen de lo que las fuentes devolvieron en la conversación (se observa con los hooks
`PostToolUse`) y de lo que el analista declaró, nunca de lo que el modelo escriba. Ante la duda se
deniega (falla cerrado).
"""

import json
import unicodedata
from dataclasses import dataclass
from typing import Any

# Política de la pasarela: raíces normalizadas de las categorías de alto riesgo (apuestas,
# criptoactivos, suplementos dietarios, venta de medicamentos). No depende del catálogo de riesgo.
HIGH_RISK_ROOTS = ("apuesta", "cripto", "suplemento", "medicament")

# Vocabulario cerrado de la recomendación de un informe, con esta grafía exacta.
RECOMMENDATIONS = ("habilitar", "no_habilitar", "escalar_a_cumplimiento")


@dataclass(frozen=True)
class Decision:
    """Resultado de aplicar una regla: permitir o bloquear, con la regla y el motivo."""

    allowed: bool
    rule: str | None
    reason: str = ""


ALLOW = Decision(True, None, "")


def normalize(text: Any) -> str:
    """Minúsculas y sin tildes; cualquier cosa que no sea texto se trata como vacía."""
    if not isinstance(text, str):
        return ""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn").strip()


def is_high_risk(text: Any) -> bool:
    """¿El texto menciona una categoría de alto riesgo de la pasarela (también con matices)?"""
    normalized = normalize(text)
    return any(root in normalized for root in HIGH_RISK_ROOTS)


def _text_of_blocks(blocks: Any) -> str | None:
    if not isinstance(blocks, list):
        return None
    texts = [b["text"] for b in blocks if isinstance(b, dict) and isinstance(b.get("text"), str)]
    return "".join(texts) if texts else None


def parse_envelope(response: Any) -> dict[str, Any] | None:
    """El sobre `{"ok":..,"content":..}` de una herramienta, o None si no se puede interpretar.

    El SDK entrega la respuesta de una herramienta MCP como texto con el JSON del servidor, aunque
    también se toleran el diccionario ya decodificado y una lista (o un diccionario `content`) de
    bloques de texto. Cualquier otra cosa no es un sobre: no se registra nada a partir de ella.
    """
    data = response
    if isinstance(data, list):
        data = _text_of_blocks(data)
    elif isinstance(data, dict) and "ok" not in data and isinstance(data.get("content"), list):
        data = _text_of_blocks(data["content"])
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError:
            return None
    if isinstance(data, dict) and "ok" in data:
        return data
    return None


# --------------------------------------------------------------------------- estado por comercio

REGISTRO = "consultar_registro_mercantil"
LISTAS = "consultar_listas_restrictivas"


@dataclass
class CommerceCase:
    """Lo que se sabe de un comercio identificado de forma unívoca durante la conversación."""

    id: str
    representante_id: str | None = None
    categoria_registro: str | None = None


def _short_name(tool: Any) -> str:
    """`mcp__pasarela-fuentes__consultar_x` -> `consultar_x`; cualquier otra cosa -> vacío."""
    return tool.rsplit("__", 1)[-1] if isinstance(tool, str) else ""


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


class CaseBook:
    """Estado de una conversación: qué devolvieron las fuentes. Una instancia por conversación.

    `observe` (PostToolUse) solo registra lo que se puede interpretar con certeza y nunca lanza:
    no registrar es lo seguro, porque todas las decisiones exigen un registro previo.
    """

    def __init__(self) -> None:
        self.commerces: dict[str, CommerceCase] = {}

    # ------------------------------------------------------------------ observación

    def observe(self, tool: Any, tool_input: Any, response: Any) -> None:
        try:
            self._observe(_short_name(tool), tool_input, response)
        except Exception:  # noqa: BLE001 - un fallo al observar nunca debe convertirse en permiso
            return

    def _observe(self, tool: str, tool_input: Any, response: Any) -> None:
        envelope = parse_envelope(response)
        if envelope is None or envelope.get("ok") is not True:
            return
        content = envelope.get("content")
        if not isinstance(content, dict):
            return
        if tool == REGISTRO:
            self._observe_registro(content)

    def _observe_registro(self, content: dict[str, Any]) -> None:
        matches = content.get("matches")
        unique = (
            content.get("match_count") == 1
            and content.get("ambiguous") is False
            and isinstance(matches, list)
            and len(matches) == 1
            and isinstance(matches[0], dict)
        )
        if not unique:
            return
        match = matches[0]
        commerce_id = _text(match.get("id"))
        if commerce_id is None or match.get("existe") is not True:
            return
        representante = match.get("representante_legal")
        case = self.commerces.get(commerce_id) or CommerceCase(commerce_id)
        case.representante_id = (
            _text(representante.get("id")) if isinstance(representante, dict) else None
        )
        case.categoria_registro = _text(match.get("categoria"))
        self.commerces[commerce_id] = case

    # ------------------------------------------------------------------ regla 1

    def check_listas(self, tool_input: Any) -> Decision:
        """Regla 1: listas solo para un comercio identificado (o para su representante legal)."""
        tipo = tool_input.get("tipo") if isinstance(tool_input, dict) else None
        referencia = _text(tool_input.get("referencia")) if isinstance(tool_input, dict) else None
        if tipo not in ("comercio", "persona") or referencia is None:
            return _deny_listas(
                "la consulta no indica un `tipo` (comercio o persona) y una `referencia` válidos"
            )
        if tipo == "comercio" and referencia in self.commerces:
            return ALLOW
        if tipo == "persona" and any(
            c.representante_id == referencia for c in self.commerces.values()
        ):
            return ALLOW
        if tipo == "comercio":
            detalle = (
                f"el comercio {referencia} no fue identificado de forma unívoca en el registro "
                "mercantil"
            )
        else:
            detalle = (
                f"la persona {referencia} no es el representante legal de un comercio identificado"
            )
        return _deny_listas(detalle)


def _deny_listas(detalle: str) -> Decision:
    return Decision(
        False,
        "1",
        "Regla 1: las listas restrictivas solo se consultan para un comercio identificado de forma "
        "unívoca en el registro mercantil (una única coincidencia existente) o para su "
        f"representante legal; {detalle}. Qué hacer: consulta primero el registro mercantil con el "
        "identificador del comercio; si devuelve varias coincidencias o ninguna, pide al analista "
        "el identificador.",
    )
