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
- **Decisión**: el SDK corre el bucle; `DueDiligenceSession.ask` itera los mensajes del turno hasta recibir `ResultMessage` y lee `subtype`, `stop_reason` y `terminal_reason`. No se configura `max_turns` ni se inspecciona el texto para decidir continuar o parar.
- **Razón**: Cumple FR-008. `max_turns` en el SDK es un tope de seguridad que dispara `error_max_turns`, no un criterio normal.
- **Nota**: el valor `tool_use` de `stop_reason` no está confirmado en la documentación (sí `end_turn`, `max_tokens`, `refusal`); el código no depende de él y solo registra el valor.
- **Verificación**: pruebas con `query` falsa: un `AssistantMessage` cuyo texto contiene "terminado" seguido de más mensajes no corta el ciclo; el ciclo termina solo en `ResultMessage`.

## D8. Pruebas sin modelo
- **Decisión**: `DueDiligenceSession(options, client_factory=ClaudeSDKClient)` recibe la fábrica del cliente; las pruebas pasan un cliente falso con `query` y `receive_response` que emite `AssistantMessage` y `ResultMessage` (dataclasses importables). Los hooks se llaman directamente con diccionarios.
- **Razón**: Los mocks de `Transport` son API de bajo nivel que puede cambiar; una costura propia es estable y simple.
- **Verificación con modelo real**: manual, en el quickstart.

## D9. Resultado de frente (contenido y metadatos)
- **Decisión**: cada subagente debe responder con un objeto JSON `{contenido, metadatos:{fuente, fecha}}` (el servidor MCP ya entrega esa separación). `events.py` intenta parsear la respuesta del subagente a `FrontResult`; si no es válida, marca el frente como `no_estructurado` en lugar de aceptarlo.
- **Razón**: No se puede *forzar* el formato del texto de un subagente; sí se puede **verificar** y no dar por bueno un resultado mal formado. El tratamiento completo de frentes fallidos es el ticket #4.
- **Alternativas**: dejar texto libre (no verificable, rompe SC-002 de procedencia más adelante).

## D11. Conversación multi-turno (decisión del usuario)
- **Decisión**: un `ClaudeSDKClient` por conversación, envuelto en `DueDiligenceSession`. `ask(texto)` hace `client.query(texto)` y recorre `client.receive_response()` hasta el `ResultMessage` del turno; el cliente conserva el contexto entre turnos.
- **Razón**: Cubre las preguntas de seguimiento (spec US1-AS3, FR-013) y el cambio de comercio a mitad de la conversación (FR-012) sin reinvestigar. La interfaz de chat (ticket #7) mantiene una sesión por conversación.
- **FR-012 con contexto compartido**: el coordinador sí ve los turnos anteriores; lo que no debe arrastrar son datos del comercio anterior hacia los *encargos*. Los subagentes siguen aislados por construcción (D3). Se verifica con el prompt y con la matriz manual (cambio de comercio).
- **Alternativas descartadas**: sesión nueva por solicitud (no permite seguimientos); `resume=session_id` sobre `query()` (válido, pero reconstruye cliente en cada turno y complica el ciclo de vida).
- **Confirmado con el SDK instalado (`claude-agent-sdk` 0.2.168, T004)**:
  - `ClaudeSDKClient(options=None, transport=None)`; `async with` conecta y desconecta; `query(prompt, session_id='default')`; `receive_response()` devuelve un iterador asíncrono de mensajes del turno.
  - `ClaudeAgentOptions` tiene `tools`, `allowed_tools`, `agents`, `mcp_servers`, `hooks`, `setting_sources`, `cwd`, `env`, `max_turns`, `forward_subagent_text`, `include_hook_events`, entre otros.
  - `AgentDefinition`: `description`, `prompt`, `tools`, `disallowedTools`, `model`, `skills`, `memory`, `mcpServers`, `initialPrompt`, `maxTurns`, `background`, `effort`, `permissionMode`.
  - `McpStdioServerConfig` solo admite `type`, `command`, `args`, `env` (**sin `cwd`**).
  - `AssistantMessage`: `content`, `parent_tool_use_id`, `stop_reason`, `message_id`, ...; `UserMessage`: `content`, `parent_tool_use_id`, `tool_use_result`; `ResultMessage`: `subtype`, `stop_reason`, `terminal_reason`, `is_error`, `num_turns`, ...; `ToolUseBlock(id, name, input)`; `ToolResultBlock(tool_use_id, content, is_error)` con `content` de tipo `str | list[dict] | None`.
  - `PreToolUseHookInput` trae `tool_name`, `tool_input`, `tool_use_id`, `agent_id`, `agent_type`; la salida de denegación usa `hookSpecificOutput.permissionDecision = "deny"` y `permissionDecisionReason`; `HookContext` solo tiene `signal`.

## D12. Coordinador con herramientas restringidas
- **Decisión**: `ClaudeAgentOptions(tools=["Agent"])` para restringir el conjunto del coordinador a la herramienta de delegación; `allowed_tools=["Agent"]` solo auto-aprueba. El hook `guards.py` niega además, dentro del coordinador, cualquier herramienta distinta de `Agent`/`Task`.
- **Razón**: según la documentación, `allowed_tools` no restringe el conjunto de herramientas disponibles; sin `tools` el coordinador conservaría Bash, Write y demás.

## D13. Arranque del servidor MCP
- **Decisión**: la configuración del servidor MCP pone `PYTHONPATH` = raíz del repositorio en su `env`, y `ClaudeAgentOptions.cwd` = raíz del repositorio, para que `python -m mcp_server` funcione sin importar desde dónde se lance el coordinador.
- **Corrección tras T004**: la primera versión de esta decisión ponía `cwd` dentro de la configuración del servidor, pero `McpStdioServerConfig` no admite `cwd`. El servidor no depende del directorio actual (sus datos y su directorio de ejecución por defecto se resuelven desde la ubicación del archivo), así que `PYTHONPATH` basta para que el módulo sea importable.

## D14. Revisión independiente del ticket (hallazgos y decisiones)
Revisión hecha por el subagente `code-reviewer` real (solo lectura). Resultado: 1 bloqueante, 7 importantes, 6 menores. Decisiones:
- **Bloqueante** — `COORDINATOR_PROMPT` no se pasaba al SDK: ahora `system_prompt=COORDINATOR_PROMPT` en `build_options()`, con prueba.
- **Permisos de herramientas MCP de subagentes**: se pre-aprueban las 4 herramientas de frente en `allowed_tools`; el coordinador sigue sin poder usarlas por el hook. **No verificable offline**: se comprueba en T025 con el modelo real (si fallara, la alternativa es que el hook devuelva `allow` explícito para la herramienta propia del subagente).
- **Cierre de turno**: todo turno termina con `RunFinished`; los casos sin resultado generan `RunFinished` de error. Solo se contiene `ResultError` (no `Exception`) y solo tras un resultado.
- **Turno abandonado**: el siguiente `ask` interrumpe y drena antes de continuar.
- **Resultados de frente**: validación estricta (contenido no vacío, fuente propia del frente, fecha ISO) y tolerante con la forma (texto previo, valla, bloques extra).
- **Hook**: deniega delegación en segundo plano; traza opcional para fijar con el SDK real el contrato de `agent_type`.
- **Verificadores de secuencia**: la dependencia exige un registro `completo`; un reintento de un frente no es violación de paralelismo. Siguen siendo verificaciones sobre eventos (no un freno en ejecución): la garantía de FR-007 es el hook del ticket #3.
- **Descartado**: duplicar frentes lanzados dos veces no se bloquea (un reintento es legítimo); `ANTHROPIC_API_KEY` sigue siendo requisito de la CLI (es el único método de autenticación documentado del SDK).
- **Sobre las pruebas de ciclo**: la revisión señaló que algunas pasarían con cualquier implementación que consuma todo el flujo. La verificación por mutación demuestra lo contrario: cortar el turno por una palabra de cierre o por un número de mensajes hace fallar esas pruebas.

## D10. Eventos para la interfaz (ticket #7)
- **Decisión**: `events.py` emite eventos de dominio: `SubagentStarted`, `SubagentFinished`, `CoordinatorText`, `RunFinished`. La atribución a subagentes usa `parent_tool_use_id` de `AssistantMessage`/`UserMessage` y los bloques `Agent`/`Task`; los hooks `SubagentStart`/`SubagentStop` entregan `agent_type`.
- **Razón**: `ToolUseBlock` no trae el subagente; la atribución viene en el mensaje.
