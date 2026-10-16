# Contrato: coordinador y subagentes

## Interfaz pública del paquete `due_diligence`

```python
class DueDiligenceSession:
    def __init__(
        self,
        options: ClaudeAgentOptions | None = None,
        client_factory=claude_agent_sdk.ClaudeSDKClient,
    ): ...
    async def __aenter__(self) -> "DueDiligenceSession": ...  # abre el cliente
    async def __aexit__(self, *exc) -> None: ...  # cierra el cliente
    async def ask(self, text: str) -> AsyncIterator[DomainEvent]: ...
```

- Una sesión = una conversación multi-turno. `ask` envía el turno del analista y emite eventos de dominio; el último evento de cada turno es siempre `RunFinished`. Si el SDK no entregó un `ResultMessage`, el `RunFinished` es de error: `subtype = error_stream_ended` (el flujo se agotó sin resultado, `terminal_reason = stream_ended`) o `subtype = error_exception` (el SDK lanzó antes de un resultado: se emite el evento terminal y la excepción se vuelve a lanzar, `terminal_reason` = nombre de la excepción).
- Solo se contiene `ResultError` del SDK y solo después de un `RunFinished`; cualquier otra excepción se propaga.
- Si el consumidor abandona `ask` a medias, el siguiente `ask` primero interrumpe (`client.interrupt()`) y drena el turno anterior hasta su `ResultMessage`, para no mezclar turnos.
- El cliente conserva el contexto entre llamadas a `ask`, así que un seguimiento no reinvestiga (FR-013).
- Terminación de un turno: **solo** al recibir el `ResultMessage` del SDK. No hay contador de iteraciones ni inspección de texto (FR-008).
- Efectos: ninguno propio; las escrituras (informes, escalamientos) las hacen las herramientas MCP.
- `client_factory` es inyectable para las pruebas (cliente falso con `query` y `receive_response`).

## Definición de subagentes (`AgentDefinition`)

| Clave | `tools` | Modelo | Prompt (resumen) |
|---|---|---|---|
| `registro_mercantil` | `mcp__pasarela-fuentes__consultar_registro_mercantil` | por defecto | Identifica al comercio con la herramienta; devuelve todas las coincidencias sin elegir; responde JSON `{contenido, metadatos}` |
| `noticias` | `mcp__pasarela-fuentes__buscar_noticias` | por defecto | Busca menciones; una mención no es coincidencia en listas; responde JSON |
| `riesgo_categoria` | `mcp__pasarela-fuentes__consultar_riesgo_categoria` | por defecto | Consulta el riesgo de la categoría recibida; si es `sin_clasificar` lo dice; responde JSON |
| `listas_restrictivas` | `mcp__pasarela-fuentes__consultar_listas_restrictivas` | por defecto | Verifica comercio y representante por identificador; responde JSON |

Todas con `description` que explica cuándo usarlas (el coordinador elige por la descripción).

## Opciones del SDK (`options.py`)

| Opción | Valor |
|---|---|
| `agents` | las 4 definiciones |
| `system_prompt` | `COORDINATOR_PROMPT` (sin él el coordinador arrancaría sin instrucciones) |
| `tools` (coordinador) | `["Agent"]` — restringe el conjunto de herramientas integradas |
| `allowed_tools` | `["Agent", *FRONT_TOOLS.values()]` — solo auto-aprueba; las 4 herramientas de frente se pre-aprueban para que los subagentes puedan usarlas, y el hook (deny gana a allow) impide que las use el coordinador o un subagente ajeno |
| `cwd` | raíz del repositorio |
| `mcp_servers` | `{"pasarela-fuentes": {type: "stdio", command: sys.executable, args: ["-m","mcp_server"], env: {PYTHONPATH: <raíz del repo>, PASARELA_FAULTS?, PASARELA_RUNTIME_DIR?}}}` (la configuración stdio del SDK no admite `cwd`) |
| `setting_sources` | `[]` |
| `hooks` | `PreToolUse` → `guards.tool_guard` (aislamiento por `agent_type`); los hooks de reglas de negocio se añaden en #3 |
| `max_turns` | no se define |
| autenticación | `ANTHROPIC_API_KEY` del entorno (nunca en el repositorio) |

## Hook `guards.tool_guard`
Entrada: `input_data` de `PreToolUse` con `tool_name` y, dentro de un subagente, `agent_type`.
- Dentro de un subagente conocido (`agent_type` ∈ frentes): permite solo su herramienta; cualquier otra → `permissionDecision: "deny"` con motivo.
- En el coordinador (sin `agent_type`): permite solo `Agent`/`Task`, solo con `subagent_type` ∈ frentes y sin `run_in_background` (en segundo plano el resultado sería un acuse, no el JSON del frente); cualquier otra herramienta (fuentes o integradas) → `deny`.
- Traza opcional: con `PASARELA_HOOK_TRACE=<ruta>` cada decisión se anota en un JSONL (`tool_name`, `agent_type`, `agent_id`, `decision`); sirve para comprobar con el modelo real qué campos entrega el SDK.
- `agent_type` desconocido: `deny` (falla cerrado).

## Formato de respuesta de un subagente
Objeto JSON: `{"contenido": {...}, "metadatos": {"fuente": "...", "fecha": "..."}}`. Se acepta con texto antes del JSON, con valla de código y con bloques extra en el resultado de la herramienta (agentId, uso); se rechaza (`no_estructurado`) si: `contenido` está vacío o no es objeto; falta `fuente` o `fecha`; `fuente` no es la del frente (la constante `SOURCE` de su herramienta en el servidor MCP); o `fecha` no es una fecha ISO válida. Un resultado de herramienta con error → `no_completado`.

## Orden esperado de eventos (solicitud válida, primer turno)
`SubagentStarted(registro_mercantil)`, `SubagentStarted(noticias)`, `SubagentStarted(riesgo_categoria)` — los tres antes de cualquier `SubagentFinished` — luego, tras el resultado del registro, `SubagentStarted(listas_restrictivas)`, y al final `CoordinatorText(informe)` y `RunFinished`.
Turno de seguimiento sobre un frente ya investigado: solo `CoordinatorText` y `RunFinished`.
