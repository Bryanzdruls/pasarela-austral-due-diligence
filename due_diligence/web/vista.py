"""Vista de cada evento del dominio para el chat: lenguaje llano, sin términos internos.

Función pura: la prueba "se entiende sin conocer el código" se comprueba sin navegador. El motivo
literal que dio la regla va siempre en el detalle; la traducción solo explica qué protege.
"""

from typing import Any

from due_diligence.events import (
    CallBlocked,
    CoordinatorText,
    DomainEvent,
    Escalated,
    FrontFinding,
    FrontName,
    FrontResult,
    FrontStatus,
    ReportRegistered,
    RunFinished,
    SubagentFinished,
    SubagentStarted,
)
from due_diligence.web.markdown import a_bloques

FRENTES = {
    FrontName.REGISTRO_MERCANTIL: "el registro mercantil",
    FrontName.LISTAS_RESTRICTIVAS: "las listas restrictivas",
    FrontName.NOTICIAS: "las noticias",
    FrontName.RIESGO_CATEGORIA: "el riesgo de la categoría",
}

REGLAS = {
    "1": "Las listas restrictivas solo se consultan para un comercio identificado con certeza.",
    "2": "Con una coincidencia en listas no se puede habilitar al comercio: se escala.",
    "3": "Un comercio de categoría de alto riesgo nunca se habilita.",
    "ambiguedad": "Con varios comercios de nombre parecido se pide el identificador; no se elige.",
    "cobertura": "Un frente caído se declara no cubierto; el informe no se presenta como completo.",
    "cobertura_habilitar": "Para habilitar hacen falta el registro y las listas consultados.",
    "conflicto": "Los datos contradictorios se muestran todos, con su origen; no se elige uno.",
    "escalamiento": "Se escala solo con un motivo real: listas, riesgo, contradicción o noticias.",
    "handoff_causa": "La causa del escalamiento debe nombrar cada motivo.",
    "handoff_hallazgos": "El resumen para cumplimiento debe traer el hallazgo que motiva el caso.",
    "identificacion": "Falta identificar el comercio antes de continuar.",
    "procedencia": "Cada afirmación del informe cita una fuente que respondió, con su fecha.",
    "reintento": "Cada consulta se reintenta como máximo una vez.",
    "vocabulario": "La recomendación debe usar uno de los valores permitidos.",
    "aislamiento": "Cada agente solo usa las herramientas de su propio frente.",
    "evaluacion": "Una regla no pudo evaluarse: por seguridad se bloquea la acción.",
}
_REGLA_GENERICA = "Una regla de la pasarela impidió esta acción."

_RECOMENDACIONES = {
    "habilitar": "habilitar",
    "no_habilitar": "no habilitar",
    "escalar_a_cumplimiento": "escalar a cumplimiento",
}
_PARADAS = {"end_turn": "el coordinador dio su respuesta", "max_tokens": "se agotó el espacio"}


def _vista(n: int, tipo: str, titulo: str, detalle: str, hora: str, **extra: Any) -> dict[str, Any]:
    return {
        "n": n,
        "tipo": tipo,
        "titulo": titulo,
        "detalle": detalle,
        "hora": hora,
        "extra": extra,
    }


def vista_analista(texto: str, hora: str, n: int = 0) -> dict[str, Any]:
    return _vista(n, "analista", "Analista", texto, hora)


def vista_error(causa: str, hora: str, n: int = 0) -> dict[str, Any]:
    return _vista(n, "error", "El turno no pudo completarse", f"Causa: {causa}", hora)


def _nombre_de(frente: str) -> str:
    try:
        return _nombre(FrontName(frente))
    except ValueError:
        return frente


def _nombre(frente: FrontName) -> str:
    return FRENTES.get(frente, str(frente.value).replace("_", " "))


def _resultado(evento: SubagentFinished, n: int) -> dict[str, Any]:
    nombre, hora = _nombre(evento.frente), evento.timestamp
    result: FrontResult | None = evento.result
    estado = result.estado if result else None
    extra = {"frente": evento.frente.value, "estado": estado.value if estado else "sin_resultado"}
    if result is not None and estado is FrontStatus.COMPLETO:
        fuente, fecha = result.metadatos["fuente"], result.metadatos["fecha"]
        detalle = f"Fuente: {fuente}. Fecha: {fecha}."
        return _vista(n, "resultado", f"Respondió {nombre}", detalle, hora, **extra)
    if result is not None and estado is FrontStatus.FALLIDO:
        error = result.contenido.get("error", {})
        partes = [f"Motivo: {error.get('motivo', 'sin detalle')}."]
        partes.append("Se puede reintentar." if error.get("reintentable") else "No se reintenta.")
        if error.get("obtenido"):
            partes.append(f"Lo obtenido antes de fallar: {error['obtenido']}.")
        return _vista(n, "resultado", f"Falló {nombre}", " ".join(partes), hora, **extra)
    return _vista(
        n,
        "resultado",
        f"La respuesta de {nombre} no se toma como completa",
        "La respuesta del frente no tenía la forma esperada; no se toma como completa.",
        hora,
        **extra,
    )


def _fin(evento: RunFinished, n: int) -> dict[str, Any]:
    if evento.subtype.startswith("error"):
        causa = evento.terminal_reason or evento.subtype
        return _vista(
            n, "error", "El turno no pudo completarse", f"Causa: {causa}.", evento.timestamp
        )
    razon = _PARADAS.get(evento.stop_reason or "", evento.stop_reason or "sin razón indicada")
    return _vista(
        n, "fin", "El coordinador terminó el turno", f"Motivo: {razon}.", evento.timestamp
    )


def a_vista(evento: DomainEvent, n: int) -> dict[str, Any]:
    """Convierte un evento del dominio en la tarjeta que ve el analista."""
    hora = evento.timestamp
    if isinstance(evento, CoordinatorText):
        bloques = a_bloques(evento.text)
        return _vista(n, "coordinador", "Coordinador", evento.text, hora, bloques=bloques)
    if isinstance(evento, FrontFinding):
        titulo = f"Hallazgo en {_nombre(evento.frente)}"
        return _vista(n, "hallazgo", titulo, evento.resumen, hora, frente=evento.frente.value)
    if isinstance(evento, SubagentStarted):
        titulo = f"Delegó en {_nombre(evento.frente)}"
        return _vista(n, "delegacion", titulo, evento.encargo, hora, frente=evento.frente.value)
    if isinstance(evento, SubagentFinished):
        return _resultado(evento, n)
    if isinstance(evento, CallBlocked):
        explicacion = REGLAS.get(evento.regla, _REGLA_GENERICA)
        # El motivo de un fallo de evaluación es el texto de una excepción: no sale del sistema.
        detalle = (
            explicacion
            if evento.regla == "evaluacion"
            else f"{explicacion} Motivo: {evento.motivo}"
        )
        titulo = "Llamada bloqueada"
        return _vista(n, "bloqueo", titulo, detalle, hora, regla=evento.regla, agente=evento.agente)
    if isinstance(evento, ReportRegistered):
        recomendacion = _RECOMENDACIONES.get(evento.recomendacion, evento.recomendacion)
        detalle = f"Comercio {evento.comercio_id}. Recomendación: {recomendacion}."
        if evento.sin_cubrir:
            nombres = ", ".join(_nombre_de(f) for f in evento.sin_cubrir)
            detalle += f" Sin cubrir: {nombres}."
        return _vista(n, "informe", f"Informe {evento.informe_id} registrado", detalle, hora)
    if isinstance(evento, Escalated):
        detalle = f"Comercio {evento.comercio_id}. Causa: {evento.causa}"
        return _vista(
            n, "escalamiento", f"Escalado a cumplimiento ({evento.escalamiento_id})", detalle, hora
        )
    if isinstance(evento, RunFinished):
        return _fin(evento, n)
    return _vista(n, "coordinador", "Evento", repr(evento), hora)
