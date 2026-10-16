"""Reglas de negocio 1 a 3 de la pasarela: lógica pura, sin SDK (ticket #3).

Las decisiones salen de lo que las fuentes devolvieron en la conversación (se observa con los hooks
`PostToolUse`) y de lo que el analista declaró, nunca de lo que el modelo escriba. Ante la duda se
deniega (falla cerrado).
"""

import json
import unicodedata
from dataclasses import dataclass, field
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
RIESGO = "consultar_riesgo_categoria"
INFORME = "registrar_informe"
ESCALAR = "escalar_a_cumplimiento"


@dataclass
class CommerceCase:
    """Lo que se sabe de un comercio identificado de forma unívoca durante la conversación."""

    id: str
    representante_id: str | None = None
    categoria_registro: str | None = None
    # Resultado de las listas por sujeto ("comercio", "persona"): True si hubo coincidencia. Solo
    # entran resultados correctos: una falla o una respuesta ilegible no es "sin coincidencias".
    listas: dict[str, bool] = field(default_factory=dict)
    # Una vez determinado que es de alto riesgo, se conserva en las solicitudes siguientes.
    alto_riesgo: bool = False
    # Solo cuando el servidor confirmó el escalamiento (`ok: true`); un error no cuenta.
    escalado: bool = False


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
        # Evidencia de la solicitud en curso (se limpia con cada solicitud nueva del analista).
        self.risk_observations: list[tuple[str, str | None]] = []
        self.declared_text = ""
        self._request_commerces: set[str] = set()
        # Categoría declarada en una solicitud que aún no tenía comercio (p. ej. "es una casa de
        # apuestas" antes de dar el nombre): la hereda el primer comercio que se identifique.
        self._carry_text = ""
        # Con un solo comercio conocido, una categoría declarada sin identificador se le aplica
        # para decidir `habilitar`, pero solo durante la solicitud: sin marca permanente ni
        # exigencia de escalar (podría referirse a un comercio nuevo aún sin identificar).
        self._fallback_commerces: set[str] = set()

    def start_request(self, prompt: Any) -> None:
        """Nueva solicitud del analista: su texto es evidencia de la categoría declarada.

        La evidencia de la solicitud solo cuenta para los comercios de esa solicitud: los que se
        identifican en ella, los que menciona por identificador y, si solo se conoce uno, ese.
        """
        if self.declared_text and not self._request_commerces:
            self._carry_text = (self._carry_text + " " + self.declared_text)[-2000:]
        self.declared_text = prompt if isinstance(prompt, str) else ""
        self.risk_observations = []
        self._request_commerces = {cid for cid in self.commerces if cid in self.declared_text}
        self._fallback_commerces = (
            set(self.commerces)
            if not self._request_commerces and len(self.commerces) == 1
            else set()
        )
        self._mark_request_commerces()

    # ------------------------------------------------------------------ observación

    def observe(self, tool: Any, tool_input: Any, response: Any) -> None:
        try:
            self._observe(_short_name(tool), tool_input, response)
        except Exception:  # noqa: BLE001 - un fallo al observar nunca debe convertirse en permiso
            return

    def _observe(self, tool: str, tool_input: Any, response: Any) -> None:
        if tool == RIESGO:
            self._observe_riesgo(tool_input, response)
        envelope = parse_envelope(response)
        if envelope is None or envelope.get("ok") is not True:
            return
        content = envelope.get("content")
        if not isinstance(content, dict):
            return
        if tool == REGISTRO:
            self._observe_registro(content)
        elif tool == LISTAS:
            self._observe_listas(tool_input, content)
        elif tool == ESCALAR:
            self._observe_escalar(tool_input)

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
        self._request_commerces.add(commerce_id)
        self._fallback_commerces.clear()  # ya hay un comercio identificado en esta solicitud
        self._mark_request_commerces()
        self._carry_text = ""  # la categoría arrastrada ya la consumió el comercio identificado

    def _observe_riesgo(self, tool_input: Any, response: Any) -> None:
        """Se anota la categoría consultada (aunque la llamada fallara) y el riesgo devuelto."""
        categoria = _text(tool_input.get("categoria")) if isinstance(tool_input, dict) else None
        if categoria is None:
            return
        envelope = parse_envelope(response)
        content = envelope.get("content") if envelope and envelope.get("ok") is True else None
        riesgo = _text(content.get("riesgo")) if isinstance(content, dict) else None
        self.risk_observations.append((categoria, riesgo))
        self._mark_request_commerces()

    def _request_evidence(self) -> bool:
        """¿Alguna fuente de la solicitud en curso indica alto riesgo? Basta una (D6)."""
        return (
            is_high_risk(self.declared_text)
            or is_high_risk(self._carry_text)
            or any(
                is_high_risk(categoria) or riesgo == "alto"
                for categoria, riesgo in self.risk_observations
            )
        )

    def _mark_request_commerces(self) -> None:
        """Los comercios identificados en esta solicitud heredan su evidencia de alto riesgo."""
        if self._request_evidence():
            for commerce_id in self._request_commerces:
                self.commerces[commerce_id].alto_riesgo = True

    def _observe_escalar(self, tool_input: Any) -> None:
        commerce_id = _text(tool_input.get("comercio_id")) if isinstance(tool_input, dict) else None
        if commerce_id in self.commerces:
            self.commerces[commerce_id].escalado = True

    def _observe_listas(self, tool_input: Any, content: dict[str, Any]) -> None:
        if not isinstance(tool_input, dict):
            return
        tipo, referencia = tool_input.get("tipo"), _text(tool_input.get("referencia"))
        match = content.get("match")
        if referencia is None or not isinstance(match, bool):
            return
        if tipo == "comercio":
            cases = [self.commerces[referencia]] if referencia in self.commerces else []
        elif tipo == "persona":
            cases = [c for c in self.commerces.values() if c.representante_id == referencia]
        else:
            return
        for case in cases:
            # Un resultado limpio posterior nunca borra una coincidencia anterior.
            case.listas[tipo] = case.listas.get(tipo, False) or match

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

    # ------------------------------------------------------------------ regla 2

    def check_informe(self, tool_input: Any) -> Decision:
        """Reglas sobre el informe que se va a registrar (la recomendación decide)."""
        data = tool_input if isinstance(tool_input, dict) else {}
        recomendacion = data.get("recomendacion")
        if not isinstance(recomendacion, str) or recomendacion not in RECOMMENDATIONS:
            return _deny_vocabulario()
        if recomendacion != "habilitar":
            return ALLOW
        case = self.commerces.get(_text(data.get("comercio_id")) or "")
        if case is None:
            return _deny_identificacion(_text(data.get("comercio_id")))
        if any(case.listas.values()):
            return _deny_regla_2(case)
        if self._is_high_risk(case):
            return _deny_regla_3(case)
        return ALLOW

    def escalation_reasons(self) -> dict[str, list[str]]:
        """Comercios con coincidencia en listas (regla 2) o de alto riesgo (regla 3) sin escalar."""
        result: dict[str, list[str]] = {}
        for commerce_id, case in self.commerces.items():
            if case.escalado:
                continue
            reasons = []
            if any(case.listas.values()):
                reasons.append("regla 2: coincidencia en listas restrictivas")
            if self._is_high_risk(case, include_fallback=False):
                reasons.append("regla 3: categoría de alto riesgo")
            if reasons:
                result[commerce_id] = reasons
        return result

    def pending_escalations(self) -> list[str]:
        """Identificadores de los comercios cuyo escalamiento está pendiente."""
        return list(self.escalation_reasons())

    def _is_high_risk(self, case: CommerceCase, include_fallback: bool = True) -> bool:
        """Regla 3: registro, catálogo o solicitud del analista; la lista de la pasarela manda."""
        in_request = case.id in self._request_commerces and self._request_evidence()
        if case.alto_riesgo or is_high_risk(case.categoria_registro) or in_request:
            case.alto_riesgo = True
        if case.alto_riesgo:
            return True
        return include_fallback and case.id in self._fallback_commerces and self._request_evidence()

    def check_escalar(self, tool_input: Any) -> Decision:
        """Escalar a un oficial de cumplimiento siempre se permite."""
        return ALLOW


def _deny_vocabulario() -> Decision:
    permitidos = ", ".join(f"`{value}`" for value in RECOMMENDATIONS)
    return Decision(
        False,
        "vocabulario",
        "La recomendación del informe debe ser exactamente uno de estos valores: "
        f"{permitidos} (en minúsculas y con guion bajo). Qué hacer: vuelve a registrar el informe "
        "con uno de ellos.",
    )


def _deny_identificacion(commerce_id: str | None) -> Decision:
    quien = f"el comercio {commerce_id}" if commerce_id else "un comercio sin identificador"
    return Decision(
        False,
        "identificacion",
        f"No se puede recomendar habilitar: {quien} no fue identificado de forma unívoca en el "
        "registro mercantil durante esta conversación. Qué hacer: identifícalo en el registro "
        "mercantil o registra el informe con `no_habilitar` o `escalar_a_cumplimiento`.",
    )


def _deny_regla_2(case: CommerceCase) -> Decision:
    quien = (
        "el representante legal"
        if case.listas.get("persona") and not case.listas.get("comercio")
        else "el comercio"
    )
    return Decision(
        False,
        "2",
        f"Regla 2: hay coincidencia en listas restrictivas de {quien} de {case.id}; no se puede "
        "recomendar habilitar. Qué hacer: escala el caso a un oficial de cumplimiento con "
        "`escalar_a_cumplimiento` (o registra el informe con `no_habilitar`).",
    )


def _deny_regla_3(case: CommerceCase) -> Decision:
    return Decision(
        False,
        "3",
        f"Regla 3: {case.id} es de una categoría de alto riesgo (apuestas, criptoactivos, "
        "suplementos dietarios o venta de medicamentos); un comercio de alto riesgo nunca recibe "
        "habilitación automática: decide un oficial de cumplimiento. Qué hacer: escala el caso a "
        "un oficial de cumplimiento con `escalar_a_cumplimiento` (o registra el informe con "
        "`no_habilitar`).",
    )


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
