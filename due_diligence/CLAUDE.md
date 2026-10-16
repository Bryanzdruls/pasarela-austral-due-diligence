# Coordinador y subagentes (`due_diligence/`)

Orquestación con el Claude Agent SDK: un coordinador delega en cuatro subagentes y sintetiza un informe. Se construye en el ticket #2 (especificación en `specs/002-coordinador-subagentes/`).

## Convenciones

- **Una herramienta por frente.** Cada subagente tiene solo la herramienta MCP de su frente; el coordinador solo tiene `Agent`. La asignación vive en un único lugar (`FRONT_TOOLS`) y la garantiza un hook `PreToolUse` que falla cerrado, no solo la configuración.
- **El ciclo termina por la razón de parada del modelo** (el `ResultMessage` del SDK). Nunca por un número fijo de iteraciones (`max_turns`) ni por buscar palabras en el texto.
- **Todo turno cierra con un evento terminal**, incluso si el SDK no entrega resultado.
- **Contexto explícito**: un subagente no hereda la conversación; recibe un encargo con lo mínimo. No se mezclan datos de un comercio con los de otro.
- **Resultados con contenido y metadatos separados**; una respuesta de subagente mal formada nunca se da por completa.
- **Las reglas de negocio 1 a 3 no se garantizan con el prompt.** Van en hooks del SDK (ticket #3). El prompt del coordinador solo orienta.
- **La regla 5 (un informe parcial no se presenta como completo) tampoco** (ticket #4): el `CaseBook` lleva el estado de cada frente con lo que devolvió el servidor; `PreToolUse` rechaza un informe o un escalamiento que no declare `sin_cubrir` un frente caído, rechaza `habilitar` sin registro y listas cubiertos y pone el tope de un reintento por solicitud (por frente en registro y noticias; por consulta en listas y riesgo). El prompt solo orienta (reintentar una vez, declarar).
- **La regla 4 también** (ticket #5): el `CaseBook` guarda las fuentes que respondieron por frente, las contradicciones que el registro señala (`conflicts` + `fuentes_registro`) y los candidatos de un resultado ambiguo; `PreToolUse` rechaza un informe o escalamiento cuyos hallazgos citen una fuente que no respondió o no traigan fecha (`procedencia`), un informe que no declare todos los valores en conflicto con su origen (`conflicto`) y uno a nombre de un candidato sin identificar (`ambiguedad`). Que el coordinador muestre los candidatos y no elija entre valores lo orienta el prompt (verificado con el modelo real, sin garantía de hook).
- Un subagente cuya fuente falla responde `{"estado": "error", ...}` (`FrontStatus.FALLIDO`); es informativo: la autoridad es el `CaseBook`.
- Las pruebas usan un cliente falso: no llaman al modelo real ni necesitan `ANTHROPIC_API_KEY`.

## Autenticación

El SDK solo usa `ANTHROPIC_API_KEY` del entorno del proceso. Nunca va en el repositorio.
