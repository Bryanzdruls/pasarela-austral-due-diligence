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
NOTICIAS = "buscar_noticias"

# Frentes de la investigación (los nombres del servidor, `PASARELA_FAULTS`) y la herramienta de
# fuente que alimenta a cada uno. Los subagentes usan otros nombres (`FrontName`): ver
# `front_of_alias`.
FRENTES = ("registro", "listas", "noticias", "riesgo")
SOURCE_TOOLS = {REGISTRO: "registro", LISTAS: "listas", NOTICIAS: "noticias", RIESGO: "riesgo"}
_FRONT_ALIASES = {
    "registro_mercantil": "registro",
    "listas_restrictivas": "listas",
    "riesgo_categoria": "riesgo",
}
# Una fuente se reintenta una vez: el intento y su reintento son dos llamadas.
MAX_ATTEMPTS = 2


def front_of_alias(name: Any) -> str | None:
    """El frente (nombre del servidor) que designa `name`, o None si no es un frente."""
    if not isinstance(name, str):
        return None
    key = normalize(name)
    key = _FRONT_ALIASES.get(key, key)
    return key if key in FRENTES else None


@dataclass(frozen=True)
class FrontFailure:
    """La última llamada fallida de un sujeto: lo que el servidor devolvió (o no pudo devolver)."""

    frente: str
    sujeto: str
    error_code: str
    retryable: bool
    obtenido: dict[str, Any] = field(default_factory=dict)


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
    # Fallos vigentes de las fuentes por (frente, sujeto); un éxito del mismo sujeto lo borra.
    fallos: dict[tuple[str, str], FrontFailure] = field(default_factory=dict)


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
        # Cobertura (ticket #4): fallos que no se pueden asociar a un comercio (se conservan hasta
        # que un comercio los adopta o la fuente responde) e intentos de la solicitud por clave de
        # intento: (fallos seguidos, si el último fue reintentable).
        self.orphan_failures: dict[tuple[str, str], FrontFailure] = {}
        self.attempts: dict[tuple[str, str], tuple[int, bool]] = {}

    def start_request(self, prompt: Any) -> None:
        """Nueva solicitud del analista: su texto es evidencia de la categoría declarada.

        La evidencia de la solicitud solo cuenta para los comercios de esa solicitud: los que se
        identifican en ella, los que menciona por identificador y, si solo se conoce uno, ese.
        """
        if self.declared_text and not self._request_commerces:
            self._carry_text = (self._carry_text + " " + self.declared_text)[-2000:]
        self.declared_text = prompt if isinstance(prompt, str) else ""
        self.risk_observations = []
        self.attempts = {}
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
        if tool in SOURCE_TOOLS:
            self._observe_coverage(SOURCE_TOOLS[tool], tool_input, envelope)
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
        self._adopt_orphans(case)
        self._mark_request_commerces()
        self._carry_text = ""  # la categoría arrastrada ya la consumió el comercio identificado

    # ------------------------------------------------------------------ cobertura (ticket #4)

    def _observe_coverage(
        self, frente: str, tool_input: Any, envelope: dict[str, Any] | None
    ) -> None:
        """Lo que devolvió una fuente: un éxito borra el fallo del sujeto; lo demás es un fallo."""
        if envelope is not None and envelope.get("ok") is True:
            self._clear_failure(frente, tool_input)
            return
        if envelope is None:
            self._record_failure(frente, tool_input, "ilegible", False, {})
            return
        partial = envelope.get("partial")
        self._record_failure(
            frente,
            tool_input,
            _text(envelope.get("error_code")) or "desconocido",
            envelope.get("retryable") is True,
            partial if isinstance(partial, dict) else {},
        )

    def observe_failure(self, tool: Any, tool_input: Any) -> None:
        """Una llamada a una fuente que falló sin devolver sobre (`PostToolUseFailure`)."""
        try:
            frente = SOURCE_TOOLS.get(_short_name(tool))
            if frente is not None:
                self._record_failure(frente, tool_input, "llamada_fallida", False, {})
        except Exception:  # noqa: BLE001 - no registrar es lo seguro: no se convierte en permiso
            return

    def _record_failure(
        self,
        frente: str,
        tool_input: Any,
        error_code: str,
        retryable: bool,
        obtenido: dict[str, Any],
    ) -> None:
        key = (frente, _subject(frente, tool_input))
        failure = FrontFailure(frente, key[1], error_code, retryable, obtenido)
        akey = _attempt_key(frente, tool_input)
        seguidos = self.attempts.get(akey, (0, True))[0]
        self.attempts[akey] = (seguidos + 1, retryable)
        self.orphan_failures.pop(key, None)
        targets = self._failure_targets(frente, tool_input)
        if not targets:
            self.orphan_failures[key] = failure
        for case in targets:
            case.fallos[key] = failure

    def _failure_targets(self, frente: str, tool_input: Any) -> list[CommerceCase]:
        """Los comercios a los que pertenece una falla; vacío si no se puede asociar a ninguno."""
        data = tool_input if isinstance(tool_input, dict) else {}
        if frente == "listas":
            referencia = _text(data.get("referencia"))
            if data.get("tipo") == "comercio" and referencia in self.commerces:
                return [self.commerces[referencia]]
            if data.get("tipo") == "persona":
                return [c for c in self.commerces.values() if c.representante_id == referencia]
            return []
        if frente == "registro":
            consulta = _text(data.get("consulta"))
            return [self.commerces[consulta]] if consulta in self.commerces else []
        scope = self._request_commerces | self._fallback_commerces
        return [self.commerces[cid] for cid in scope if cid in self.commerces]

    def _clear_failure(self, frente: str, tool_input: Any) -> None:
        """Un éxito borra el fallo de su sujeto, pero solo en los comercios a los que pertenece:
        el éxito de noticias de un comercio no cubre el de otro."""
        key = (frente, _subject(frente, tool_input))
        self.attempts.pop(_attempt_key(frente, tool_input), None)
        self.orphan_failures.pop(key, None)
        for case in self._failure_targets(frente, tool_input):
            case.fallos.pop(key, None)

    def _adopt_orphans(self, case: CommerceCase) -> None:
        """El registro identificó un comercio: adopta las fallas de noticias y riesgo (corren en
        paralelo con el registro) y descarta las del propio registro, que ya respondió."""
        for key, failure in list(self.orphan_failures.items()):
            if failure.frente in ("noticias", "riesgo"):
                case.fallos[key] = failure
                del self.orphan_failures[key]
            elif failure.frente == "registro":
                del self.orphan_failures[key]

    def failed_fronts(self, commerce_id: Any) -> dict[str, FrontFailure]:
        """Frentes con un fallo vigente del comercio, incluidos los huérfanos de la solicitud."""
        key = commerce_id.strip() if isinstance(commerce_id, str) else None
        case = self.commerces.get(key) if key else None
        failures = [*(case.fallos.values() if case else ()), *self.orphan_failures.values()]
        result: dict[str, FrontFailure] = {}
        for failure in failures:
            result.setdefault(failure.frente, failure)
        return result

    def check_fuente(self, tool: Any, tool_input: Any) -> Decision:
        """Tope de reintentos: se reintenta una vez, y nunca una falla no reintentable."""
        frente = SOURCE_TOOLS.get(_short_name(tool))
        if frente is None:
            return ALLOW
        state = self.attempts.get(_attempt_key(frente, tool_input))
        if state is None:
            return ALLOW
        seguidos, retryable = state
        if not retryable:
            return _deny_reintento(frente, "la falla no es reintentable")
        if seguidos >= MAX_ATTEMPTS:
            return _deny_reintento(frente, "ya se reintentó una vez y volvió a fallar")
        return ALLOW

    def _check_cobertura(self, data: dict[str, Any]) -> Decision | None:
        """Todo frente con un fallo vigente debe constar como `sin_cubrir` en la cobertura."""
        failed = self.failed_fronts(_text(data.get("comercio_id")))
        declared = _declared_fronts(data.get("cobertura"))
        missing = [frente for frente in FRENTES if frente in failed and frente not in declared]
        return _deny_cobertura(missing) if missing else None

    def _listas_faltantes(self, case: CommerceCase) -> list[str]:
        """Lo que falta de las listas para habilitar: el comercio y su representante legal."""
        faltan = []
        if "comercio" not in case.listas:
            faltan.append("del comercio")
        if case.representante_id is not None and "persona" not in case.listas:
            faltan.append("de su representante legal")
        return faltan

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
        if (sin_declarar := self._check_cobertura(data)) is not None:
            return sin_declarar
        if recomendacion != "habilitar":
            return ALLOW
        case = self.commerces.get(_text(data.get("comercio_id")) or "")
        if case is None:
            return _deny_identificacion(_text(data.get("comercio_id")))
        if any(case.listas.values()):
            return _deny_regla_2(case)
        if self._is_high_risk(case):
            return _deny_regla_3(case)
        if faltan := self._listas_faltantes(case):
            return _deny_cobertura_habilitar(case, faltan)
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
        """Escalar se permite, declarando los frentes sin cubrir para que el oficial lo sepa."""
        data = tool_input if isinstance(tool_input, dict) else {}
        return self._check_cobertura(data) or ALLOW


def _subject(frente: str, tool_input: Any) -> str:
    """Qué identifica una consulta, normalizado: reescribirla no la convierte en otra consulta."""
    data = tool_input if isinstance(tool_input, dict) else {}
    if frente in ("registro", "noticias"):
        # La fuente responde o no, sea cual sea la redacción de la consulta: con el modelo real un
        # subagente reintentó noticias con tres redacciones distintas.
        return "*"
    if frente == "listas":
        return f"{normalize(data.get('tipo'))}:{normalize(data.get('referencia'))}"
    return normalize(data.get("categoria"))


def _attempt_key(frente: str, tool_input: Any) -> tuple[str, str]:
    """Qué se cuenta para el tope de reintentos: el frente entero, salvo en listas, donde el
    comercio y su representante son consultas distintas. Con el modelo real, noticias se
    reintentó con tres redacciones; la categoría de riesgo es texto libre y se esquiva igual."""
    return (frente, _subject(frente, tool_input) if frente == "listas" else "*")


def _declared_fronts(cobertura: Any) -> set[str]:
    """Frentes que la cobertura declara `sin_cubrir`; cualquier otra forma no declara nada."""
    if not isinstance(cobertura, dict):
        return set()
    return {
        frente
        for name, value in cobertura.items()
        if (frente := front_of_alias(name)) is not None
        and isinstance(value, dict)
        and value.get("estado") == "sin_cubrir"
    }


def _deny_reintento(frente: str, motivo: str) -> Decision:
    return Decision(
        False,
        "reintento",
        f"No se vuelve a consultar la fuente de {frente}: {motivo}. Qué hacer: no la llames otra "
        "vez; responde con el error estructurado (frente, lo obtenido y si es reintentable) y "
        "el frente se declarará sin cubrir en el informe.",
    )


def _deny_cobertura(missing: list[str]) -> Decision:
    frentes = ", ".join(f"`{frente}`" for frente in missing)
    ejemplo = '{"' + missing[0] + '": {"estado": "sin_cubrir", "motivo": "..."}}'
    return Decision(
        False,
        "cobertura",
        "Regla 5: un informe parcial no puede presentarse como completo. Faltan por declarar "
        f"como sin cubrir: {frentes}; la fuente no respondió y no constan así en `cobertura`. "
        "Qué hacer: vuelve a llamar a la herramienta con `cobertura` declarando cada uno, p. ej. "
        f"{ejemplo}.",
    )


def _deny_cobertura_habilitar(case: CommerceCase, faltan: list[str]) -> Decision:
    detalle = " y ".join(faltan)
    return Decision(
        False,
        "cobertura_habilitar",
        f"No se puede recomendar habilitar {case.id}: las listas restrictivas {detalle} no se "
        "consultaron con éxito. Qué hacer: consúltalas con `consultar_listas_restrictivas` o "
        "registra el informe con `no_habilitar` o `escalar_a_cumplimiento`, declarando el frente "
        "`listas` como sin cubrir.",
    )


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
