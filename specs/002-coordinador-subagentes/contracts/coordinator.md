# Contrato: coordinador y subagentes

## Interfaz pública del paquete `due_diligence`

```python
async def run_due_diligence(
    request: str,
    query_fn=claude_agent_sdk.query,   # inyectable para pruebas
    options: ClaudeAgentOptions | None = None,
) -> AsyncIterator[DomainEvent]
```

- Entrada: el texto del analista.
- Salida: flujo de eventos de dominio (ver [data-model.md](../data-model.md)); el último es siempre `RunFinished`.
- Terminación: **solo** al recibir `ResultMessage` del SDK. No hay contador de iteraciones ni inspección de texto (FR-008).
- Efectos: ninguno propio; las escrituras (informes, escalamientos) las hacen las herramientas MCP.

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
| `allowed_tools` (coordinador) | `["Agent"]` |
| `mcp_servers` | `{"pasarela-fuentes": {command: sys.executable, args: ["-m","mcp_server"], env: {...}}}` |
| `setting_sources` | `[]` |
| `hooks` | `PreToolUse` → `guards.tool_guard` (aislamiento por `agent_type`); los hooks de reglas de negocio se añaden en #3 |
| `max_turns` | no se define |
| autenticación | `ANTHROPIC_API_KEY` del entorno (nunca en el repositorio) |

## Hook `guards.tool_guard`
Entrada: `input_data` de `PreToolUse` con `tool_name` y, dentro de un subagente, `agent_type`.
- Si `agent_type` es un frente conocido y `tool_name` no está en su lista: devuelve `permissionDecision: "deny"` con motivo.
- Si no hay `agent_type` (coordinador): permite solo `Agent`/`Task`; cualquier otra herramienta de fuentes la niega (el coordinador no consulta fuentes directamente).
- En cualquier otro caso: `{}`.

## Formato de respuesta de un subagente
Objeto JSON: `{"contenido": {...}, "metadatos": {"fuente": "...", "fecha": "..."}}`. Una respuesta que no cumple se marca `no_estructurado`.

## Orden esperado de eventos (solicitud válida)
`SubagentStarted(registro_mercantil)`, `SubagentStarted(noticias)`, `SubagentStarted(riesgo_categoria)` — los tres antes de cualquier `SubagentFinished` — luego, tras el resultado del registro, `SubagentStarted(listas_restrictivas)`, y al final `CoordinatorText(informe)` y `RunFinished`.
