# Research: Coordinador y subagentes

Fuente: documentación del Claude Agent SDK para Python consultada el 2026-10-14 (code.claude.com/docs/en/agent-sdk: `python`, `subagents`, `agent-loop`, `hooks`, `mcp`). Lo no confirmado en la documentación se marca así y se verifica con una prueba.

## D1. Paquete y autenticación
- **Decisión**: `claude-agent-sdk` (≥ 0.2.140; verificada la 0.2.166), autenticación con `ANTHROPIC_API_KEY` en el entorno del proceso. El wheel incluye el binario de Claude Code.
- **Razón**: Es el único método documentado; el login de Claude Code/claude.ai no está permitido para productos de terceros.
- **Consecuencia**: la ejecución real necesita una API key del analista que corre el sistema; no va en el repositorio. Las pruebas automáticas no la necesitan (D8). `.env.example` solo trae el nombre de la variable, sin valor.
- **Alternativas**: Bedrock/Vertex (`CLAUDE_CODE_USE_*`): válidas, pero sin necesidad aquí.

## D2. Subagentes con `AgentDefinition`
- **Decisión**: cuatro `AgentDefinition` (registro_mercantil, listas_restrictivas, noticias, riesgo_categoria) pasadas en `ClaudeAgentOptions(agents=...)`. El coordinador las invoca con la herramienta `Agent` (alias `Task`), que debe estar en `allowed_tools` del coordinador.
- **Razón**: Es el mecanismo del SDK para subagentes con prompt y herramientas propios, y no heredan la conversación (D3).
- **Nota**: en Python los campos multipalabra de `AgentDefinition` conservan camelCase (`disallowedTools`, `maxTurns`, `mcpServers`).
- **Alternativas**: orquestar en código con varias llamadas `query()` (coordinador "falso", sin bucle agéntico real: no cumple el comportamiento 1 del enunciado); subagentes como archivos `.claude/agents` (son de Claude Code para desarrollar, no del sistema).

## D3. Aislamiento de contexto
- **Decisión**: el subagente recibe solo su `prompt` de definición y el texto del encargo que el coordinador le pasa; `setting_sources=[]` para que no herede la configuración del proyecto de desarrollo (CLAUDE.md, reglas).
- **Razón**: El SDK ya aísla la conversación; `setting_sources=[]` evita que el contexto de *desarrollo* contamine un producto que debe ser independiente.
- **Verificación**: prueba de que el encargo enviado al subagente contiene solo lo necesario (SC-003).

## D4. Herramientas por frente (restricción en dos capas)
- **Decisión**:
  1. Configuración: `AgentDefinition.tools = ["mcp__pasarela-fuentes__<herramienta de su frente>"]`.
  2. Respaldo determinista: hook `PreToolUse` (`guards.py`) que niega cualquier herramienta fuera de la lista del `agent_type` que llama (el hook recibe `agent_type`).
- **Razón**: La documentación no confirma que `tools=["mcp__..."]` restrinja herramientas MCP concretas dentro de un subagente. Con el hook la garantía no depende de ese detalle y se prueba sin modelo (el hook es una función async).
- **Alternativas**: solo `tools` (riesgo de no restringir sin saberlo); `disallowedTools` con `mcp__pasarela-fuentes__*` (quita todo el servidor, no permite dejar solo una).

## D5. Servidor MCP del ticket #1
- **Decisión**: `mcp_servers={"pasarela-fuentes": {"command": sys.executable, "args": ["-m", "mcp_server"], "env": {...}}}` (stdio). El nombre `pasarela-fuentes` coincide con `.mcp.json`, así las herramientas se llaman `mcp__pasarela-fuentes__<nombre>`.
- **Razón**: Reutiliza el servidor tal cual, sin importarlo en el mismo proceso; `PASARELA_FAULTS` y `PASARELA_RUNTIME_DIR` se pasan por `env`.

## D6. Paralelismo y dependencia
- **Decisión**: el prompt del coordinador le indica lanzar `registro_mercantil`, `noticias` y `riesgo_categoria` en **un mismo turno** (varias llamadas `Agent` a la vez) y esperar sus resultados; solo después lanzar `listas_restrictivas`, pasándole el identificador y el representante legal que devolvió el registro.
- **Razón**: El SDK ejecuta subagentes de forma concurrente cuando el modelo emite varias llamadas en un turno. En Python no hay primitiva documentada para "B después de A" (la herramienta `Workflow` es solo TypeScript), pero aquí la dependencia es de **datos**: listas necesita lo que devuelve el registro, así que el coordinador no puede lanzarla antes.
- **Garantía**: la dependencia se refuerza con un hook en el ticket #3; aquí es comportamiento orientado por prompt y verificado por la secuencia de eventos.
- **Alternativas**: `asyncio.gather` sobre `query()` independientes (el coordinador dejaría de ser un agente); `resume=session_id` encadenado (más complejo sin beneficio).

## D7. Ciclo agéntico y razón de parada
- **Decisión**: el SDK corre el bucle; `coordinator.run_due_diligence` itera los mensajes hasta recibir `ResultMessage` y lee `subtype`, `stop_reason` y `terminal_reason`. No se configura `max_turns` ni se inspecciona el texto para decidir continuar o parar.
- **Razón**: Cumple FR-008. `max_turns` en el SDK es un tope de seguridad que dispara `error_max_turns`, no un criterio normal.
- **Nota**: el valor `tool_use` de `stop_reason` no está confirmado en la documentación (sí `end_turn`, `max_tokens`, `refusal`); el código no depende de él y solo registra el valor.
- **Verificación**: pruebas con `query` falsa: un `AssistantMessage` cuyo texto contiene "terminado" seguido de más mensajes no corta el ciclo; el ciclo termina solo en `ResultMessage`.

## D8. Pruebas sin modelo
- **Decisión**: `run_due_diligence(request, query_fn=query)` recibe la función de consulta; las pruebas pasan una `query` falsa que emite `AssistantMessage` y `ResultMessage` (dataclasses importables). Los hooks se llaman directamente con diccionarios.
- **Razón**: Los mocks de `Transport` son API de bajo nivel que puede cambiar; una costura propia es estable y simple.
- **Verificación con modelo real**: manual, en el quickstart.

## D9. Resultado de frente (contenido y metadatos)
- **Decisión**: cada subagente debe responder con un objeto JSON `{contenido, metadatos:{fuente, fecha}}` (el servidor MCP ya entrega esa separación). `events.py` intenta parsear la respuesta del subagente a `FrontResult`; si no es válida, marca el frente como `no_estructurado` en lugar de aceptarlo.
- **Razón**: No se puede *forzar* el formato del texto de un subagente; sí se puede **verificar** y no dar por bueno un resultado mal formado. El tratamiento completo de frentes fallidos es el ticket #4.
- **Alternativas**: dejar texto libre (no verificable, rompe SC-002 de procedencia más adelante).

## D10. Eventos para la interfaz (ticket #7)
- **Decisión**: `events.py` emite eventos de dominio: `SubagentStarted`, `SubagentFinished`, `CoordinatorText`, `RunFinished`. La atribución a subagentes usa `parent_tool_use_id` de `AssistantMessage`/`UserMessage` y los bloques `Agent`/`Task`; los hooks `SubagentStart`/`SubagentStop` entregan `agent_type`.
- **Razón**: `ToolUseBlock` no trae el subagente; la atribución viene en el mensaje.
