# Coordinador y subagentes (`due_diligence/`)

Orquestación con el Claude Agent SDK: un coordinador delega en cuatro subagentes y sintetiza un informe. Se construye en el ticket #2 (especificación en `specs/002-coordinador-subagentes/`).

## Convenciones

- **Una herramienta por frente.** Cada subagente tiene solo la herramienta MCP de su frente; el coordinador solo tiene `Agent`. La asignación vive en un único lugar (`FRONT_TOOLS`) y la garantiza un hook `PreToolUse` que falla cerrado, no solo la configuración.
- **El ciclo termina por la razón de parada del modelo** (el `ResultMessage` del SDK). Nunca por un número fijo de iteraciones (`max_turns`) ni por buscar palabras en el texto.
- **Todo turno cierra con un evento terminal**, incluso si el SDK no entrega resultado.
- **Contexto explícito**: un subagente no hereda la conversación; recibe un encargo con lo mínimo. No se mezclan datos de un comercio con los de otro.
- **Resultados con contenido y metadatos separados**; una respuesta de subagente mal formada nunca se da por completa.
- **Las reglas de negocio 1 a 3 no se garantizan con el prompt.** Van en hooks del SDK (ticket #3). El prompt del coordinador solo orienta.
- Las pruebas usan un cliente falso: no llaman al modelo real ni necesitan `ANTHROPIC_API_KEY`.

## Autenticación

El SDK solo usa `ANTHROPIC_API_KEY` del entorno del proceso. Nunca va en el repositorio.
