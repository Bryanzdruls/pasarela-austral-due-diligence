# Contrato: reglas y hooks

## Módulo `due_diligence/rules.py` (puro, sin SDK)

```text
HIGH_RISK_ROOTS = ("apuesta", "cripto", "suplemento", "medicament")
RECOMMENDATIONS = ("habilitar", "no_habilitar", "escalar_a_cumplimiento")

is_high_risk(text: str) -> bool            # normaliza y busca las raíces
Decision(allowed: bool, rule: str | None, reason: str)

CaseBook:
  observe(tool: str, tool_input: dict, response: Any) -> None   # PostToolUse; nunca lanza
  start_request(prompt: str) -> None                            # UserPromptSubmit
  check_listas(tool_input: dict) -> Decision                    # regla 1
  check_informe(tool_input: dict) -> Decision                   # vocabulario, reglas 2 y 3, FR-010
  check_escalar(tool_input: dict) -> Decision                   # siempre permite
  pending_escalations() -> list[str]                            # comercios con regla 2 o 3 sin escalar
```

`tool` es el nombre corto de la herramienta (`consultar_registro_mercantil`, `consultar_listas_restrictivas`, `consultar_riesgo_categoria`). `response` puede ser texto, diccionario o lista de bloques; si no se puede interpretar, `observe` no registra nada.

## Hooks (`due_diligence/rule_hooks.py`)

| Hook | Evento | Qué hace |
|---|---|---|
| `make_pre_tool_use(book)` | `PreToolUse` | Para `consultar_listas_restrictivas`, `registrar_informe` y `escalar_a_cumplimiento` consulta el `CaseBook` y devuelve la denegación del SDK si no se permite; el resto lo decide el guard de aislamiento |
| `make_post_tool_use(book)` | `PostToolUse` | Llama a `book.observe` con el nombre corto, la entrada y la respuesta; nunca lanza ni bloquea |
| `make_user_prompt_submit(book)` | `UserPromptSubmit` | Llama a `book.start_request(prompt)` |
| `make_stop(book)` | `Stop` | Si `book.pending_escalations()` no está vacío y `stop_hook_active` no es verdadero, devuelve `{"decision": "block", "reason": ...}` pidiendo escalar; si no, `{}` |

Forma de la denegación (la misma del guard del #2):

```json
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
 "permissionDecisionReason": "Regla 1: ... Qué hacer: ..."}}
```

Una excepción en un hook `PreToolUse` de reglas produce una denegación (falla cerrado).

## Cambios en lo existente

- `guards.py`: el coordinador (sin `agent_type`) puede usar `Agent`/`Task` (como hoy) y además `mcp__pasarela-fuentes__registrar_informe` y `mcp__pasarela-fuentes__escalar_a_cumplimiento`. Ningún subagente puede usar esas dos.
- `options.py`: `build_options(book: CaseBook | None = None)` crea o recibe el `CaseBook`, registra `PreToolUse` (guard y reglas), `PostToolUse` y `UserPromptSubmit`, y añade las dos herramientas a `allowed_tools`.
- `coordinator.py`: `DueDiligenceSession` crea un `CaseBook` por conversación cuando construye sus opciones.
- `prompts.py`: el coordinador conoce el vocabulario y que debe registrar el informe con `registrar_informe` y, si corresponde, escalar con `escalar_a_cumplimiento`; el texto sigue diciendo que las reglas se imponen con hooks.

## Mensajes de denegación (contenido mínimo)

| Regla | El mensaje dice |
|---|---|
| 1 | que las listas solo se consultan para un comercio identificado de forma unívoca en el registro y qué falta (sin registro, ambiguo, otro identificador, persona que no es el representante) |
| 2 | que hay coincidencia en listas y que no se puede recomendar habilitar: escalar a un oficial de cumplimiento |
| 3 | que el comercio es de alto riesgo y que decide un oficial de cumplimiento |
| vocabulario | los valores permitidos |
| FR-010 | que el comercio no fue identificado de forma unívoca |
