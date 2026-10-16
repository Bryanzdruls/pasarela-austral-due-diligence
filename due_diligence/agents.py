"""Definición de los cuatro subagentes: cada uno con una sola herramienta de su frente."""

from claude_agent_sdk import AgentDefinition

from due_diligence.events import FrontName
from due_diligence.prompts import SUBAGENT_PROMPTS

_PREFIX = "mcp__pasarela-fuentes__"

# Única fuente de verdad de qué herramienta puede usar cada frente.
FRONT_TOOLS: dict[FrontName, str] = {
    FrontName.REGISTRO_MERCANTIL: _PREFIX + "consultar_registro_mercantil",
    FrontName.LISTAS_RESTRICTIVAS: _PREFIX + "consultar_listas_restrictivas",
    FrontName.NOTICIAS: _PREFIX + "buscar_noticias",
    FrontName.RIESGO_CATEGORIA: _PREFIX + "consultar_riesgo_categoria",
}

_DESCRIPTIONS: dict[FrontName, str] = {
    FrontName.REGISTRO_MERCANTIL: (
        "Identifica al comercio en el registro mercantil por nombre o identificador y devuelve "
        "su existencia, fecha de constitución, representante legal y estado. Úsalo primero y "
        "siempre: de él dependen las listas restrictivas."
    ),
    FrontName.LISTAS_RESTRICTIVAS: (
        "Verifica al comercio y a su representante legal contra las listas restrictivas, por "
        "identificador. Úsalo solo después de que el registro mercantil haya identificado de "
        "forma unívoca al comercio."
    ),
    FrontName.NOTICIAS: (
        "Busca menciones del comercio o de su representante en el corpus de noticias. Úsalo en "
        "paralelo con el registro mercantil y el riesgo de categoría."
    ),
    FrontName.RIESGO_CATEGORIA: (
        "Consulta el nivel de riesgo de la categoría de negocio del comercio. Úsalo en paralelo "
        "con el registro mercantil y las noticias."
    ),
}


def build_agents() -> dict[str, AgentDefinition]:
    return {
        front.value: AgentDefinition(
            description=_DESCRIPTIONS[front],
            prompt=SUBAGENT_PROMPTS[front.value],
            tools=[FRONT_TOOLS[front]],
            background=False,  # el coordinador necesita el resultado del frente, no un acuse
        )
        for front in FrontName
    }
